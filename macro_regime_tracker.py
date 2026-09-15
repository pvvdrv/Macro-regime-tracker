import numpy as np
import pandas as pd
import plotly.graph_objects as go
from fredapi import Fred
import yfinance as yf


class MacroRegimeTracker:
    def __init__(self, fred_api_key: str):
        self.fred = Fred(api_key=fred_api_key)
        self.tickers = ['SPY', 'TLT', 'GLD', 'DBC']
        self.macro_data = None
        self.market_data = None
        self.backtest_data = None

    def fetch_macro_data(self):
        """Pulls Growth, Inflation, and Yield Curve series from FRED."""
        print("Fetching macro data from FRED...")
        indpro = self.fred.get_series('INDPRO')
        cpi = self.fred.get_series('CPIAUCSL')
        yield_curve = self.fred.get_series('T10Y2Y')

        df = pd.DataFrame({
            'Growth': indpro,
            'Inflation': cpi,
            'Yield_Curve': yield_curve
        })

        # Resample to month-end and apply a 1-month lag to prevent look-ahead bias
        self.macro_data = df.resample('ME').last().shift(1).dropna()

    def fetch_market_data(self):
        """Pulls monthly close prices for asset ETFs from Yahoo Finance."""
        print("Fetching market data from Yahoo Finance...")
        prices = yf.download(self.tickers, start="2006-02-01", interval="1mo")['Close']
        prices.index = pd.to_datetime(prices.index).tz_localize(None)
        self.market_data = prices.resample('ME').last()

    def generate_signals(self):
        """Calculates momentum against 6-month SMAs and classifies regimes."""
        print("Generating macro signals and regimes...")
        df = self.macro_data.copy()

        # Growth & Inflation: YoY % change minus 6-month rolling average
        df_yoy = df[['Growth', 'Inflation']].pct_change(12) * 100
        df_sma = df_yoy.rolling(window=6).mean()
        momentum = (df_yoy - df_sma).dropna()

        # Liquidity: 10Y-2Y spread level minus 6-month rolling average
        yc_sma = df['Yield_Curve'].rolling(window=6).mean()
        liq_momentum = (df['Yield_Curve'] - yc_sma).dropna()

        signals = momentum.join(liq_momentum.rename('Liq_Momentum'), how='inner')

        # 4-Quadrant growth/inflation logic + liquidity overlay
        def classify(row):
            g, i, l = row['Growth'], row['Inflation'], row['Liq_Momentum']
            if g > 0 and i <= 0:
                regime = 'Goldilocks'
            elif g > 0 and i > 0:
                regime = 'Reflation'
            elif g <= 0 and i > 0:
                regime = 'Stagflation'
            else:
                regime = 'Deflation'

            liquidity = 'Easing' if l > 0 else 'Tightening'
            return pd.Series([regime, liquidity, f"{regime} & {liquidity}"])

        signals[['Regime', 'Liquidity', '3D_Regime']] = signals.apply(classify, axis=1)
        self.macro_data = signals

    def run_backtest(self):
        """Executes asset allocation based on regime signals and tracks compounding returns."""
        print("Running backtest simulation...")
        returns = self.market_data.pct_change() * 100
        
        # Shift returns back by 1 month to pair signal at t with performance over t+1
        fwd_returns = returns.shift(-1).dropna()
        fwd_returns.columns = [f"{col}_Fwd_Return" for col in fwd_returns.columns]

        bt = self.macro_data[['Regime']].join(fwd_returns, how='inner').dropna()

        # Target asset mapping per regime
        def select_asset(row):
            reg = row['Regime']
            if reg == 'Goldilocks':
                return row['SPY_Fwd_Return']
            elif reg == 'Reflation':
                return row['DBC_Fwd_Return']
            elif reg == 'Stagflation':
                return row['GLD_Fwd_Return']
            elif reg == 'Deflation':
                return row['TLT_Fwd_Return']
            return 0.0

        bt['Strategy_Return'] = bt.apply(select_asset, axis=1)

        # Compound cumulative portfolio values from a $100 starting base
        bt['Strategy_Equity'] = 100 * (1 + bt['Strategy_Return'] / 100).cumprod()
        bt['SPY_Equity'] = 100 * (1 + bt['SPY_Fwd_Return'] / 100).cumprod()

        self.backtest_data = bt

    def print_performance(self):
        """Computes and displays CAGR, Volatility, Sharpe Ratio, and Max Drawdown."""
        bt = self.backtest_data
        years = len(bt) / 12

        def calc_metrics(equity_col, return_col):
            cagr = (bt[equity_col].iloc[-1] / 100) ** (1 / years) - 1
            vol = (bt[return_col] / 100).std() * np.sqrt(12)
            sharpe = cagr / vol if vol != 0 else 0.0
            peak = bt[equity_col].cummax()
            mdd = ((bt[equity_col] - peak) / peak).min()
            return cagr, vol, sharpe, mdd

        spy_cagr, spy_vol, spy_sharpe, spy_mdd = calc_metrics('SPY_Equity', 'SPY_Fwd_Return')
        strat_cagr, strat_vol, strat_sharpe, strat_mdd = calc_metrics('Strategy_Equity', 'Strategy_Return')

        print("\n" + "=" * 48)
        print("         STRATEGY PERFORMANCE VS S&P 500       ")
        print("=" * 48)
        print(f"{'Metric':<16} | {'S&P 500 (SPY)':<14} | {'Macro Strategy':<14}")
        print("-" * 48)
        print(f"{'CAGR':<16} | {spy_cagr * 100:>12.2f}% | {strat_cagr * 100:>12.2f}%")
        print(f"{'Volatility (Ann)':<16} | {spy_vol * 100:>12.2f}% | {strat_vol * 100:>12.2f}%")
        print(f"{'Sharpe Ratio':<16} | {spy_sharpe:>13.2f} | {strat_sharpe:>13.2f}")
        print(f"{'Max Drawdown':<16} | {spy_mdd * 100:>12.2f}% | {strat_mdd * 100:>12.2f}%")
        print("=" * 48 + "\n")

    def plot_regimes(self):
        """Exports interactive regime history with background shading to HTML."""
        print("Generating regime chart...")
        common_dates = self.macro_data.index.intersection(self.market_data.index)
        plot_macro = self.macro_data.loc[common_dates]
        prices = self.market_data[self.tickers].loc[common_dates]
        normalized_prices = (prices / prices.iloc[0]) * 100

        fig = go.Figure()

        # Regime background highlights
        regime_colors = {
            'Goldilocks': 'lightgreen',
            'Reflation': 'orange',
            'Stagflation': 'lightcoral',
            'Deflation': 'lightblue'
        }
        for regime, color in regime_colors.items():
            y_vals = [5000 if r == regime else 0 for r in plot_macro['Regime']]
            fig.add_trace(go.Scatter(
                x=plot_macro.index,
                y=y_vals,
                fill='tozeroy',
                mode='none',
                fillcolor=color,
                opacity=0.3,
                name=f"Regime: {regime}",
                hoverinfo='skip',
                line_shape='hv'
            ))

        # Normalized asset price paths
        line_colors = {'SPY': 'black', 'TLT': 'blue', 'GLD': 'gold', 'DBC': 'brown'}
        for ticker in self.tickers:
            fig.add_trace(go.Scatter(
                x=normalized_prices.index,
                y=normalized_prices[ticker],
                mode='lines',
                name=ticker,
                line=dict(color=line_colors[ticker], width=2)
            ))

        # Historical crisis callouts
        key_events = [
            {"date": "2008-09-30", "text": "Lehman Collapse<br>(Deflation)"},
            {"date": "2020-03-31", "text": "COVID Crash<br>(Deflation)"},
            {"date": "2022-03-31", "text": "Rate Hike Cycle<br>(Stagflation)"}
        ]
        for event in key_events:
            try:
                y_loc = normalized_prices.loc[event["date"], 'SPY']
            except KeyError:
                y_loc = 100
            fig.add_annotation(
                x=event["date"],
                y=y_loc,
                text=event["text"],
                showarrow=True,
                arrowhead=2,
                ax=-40,
                ay=-60,
                bgcolor="white",
                bordercolor="black"
            )

        max_val = normalized_prices.max().max() * 1.15
        fig.update_layout(
            title="Macroeconomic Regime History & Asset Normalization (Base = 100)",
            yaxis_title="Normalized Value",
            xaxis_title="Date",
            hovermode="x unified",
            template="plotly_white",
            height=650,
            yaxis=dict(range=[0, max_val])
        )
        fig.write_html("regime_chart.html", auto_open=True)

    def plot_equity_curve(self):
        """Exports interactive backtest equity curve to HTML."""
        print("Generating equity curve chart...")
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=self.backtest_data.index,
            y=self.backtest_data['Strategy_Equity'],
            mode='lines',
            name='Macro Regime Strategy',
            line=dict(color='darkblue', width=2.5)
        ))
        fig.add_trace(go.Scatter(
            x=self.backtest_data.index,
            y=self.backtest_data['SPY_Equity'],
            mode='lines',
            name='Benchmark: S&P 500 (SPY)',
            line=dict(color='gray', width=2, dash='dash')
        ))

        fig.update_layout(
            title="Equity Curve Simulation: Macro Rotation vs. Buy-and-Hold SPY",
            yaxis_title="Portfolio Value ($)",
            xaxis_title="Date",
            hovermode="x unified",
            template="plotly_white",
            height=600
        )
        fig.write_html("equity_curve_chart.html", auto_open=True)


if __name__ == "__main__":
    API_KEY = "YOUR_FRED_API_KEY"

    tracker = MacroRegimeTracker(fred_api_key=API_KEY)
    tracker.fetch_macro_data()
    tracker.fetch_market_data()
    tracker.generate_signals()
    tracker.run_backtest()
    tracker.print_performance()

    tracker.plot_regimes()
    tracker.plot_equity_curve()
