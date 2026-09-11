import pandas as pd
import numpy as np
import yfinance as yf
from fredapi import Fred
import plotly.graph_objects as go

class MacroRegimeTracker:
    """
    A Rule-Based Macro Regime Tracker that classifies the economic environment 
    based on Growth, Inflation, and Liquidity momentum, and backtests a dynamic 
    asset allocation strategy.
    """
    
    def __init__(self, fred_api_key):
        self.fred = Fred(api_key=fred_api_key)
        self.tickers = ['SPY', 'TLT', 'GLD', 'DBC']
        self.macro_data = None
        self.market_data = None
        self.backtest_data = None

    def fetch_macro_data(self):
        print("Fetching Macro Data from FRED...")
        indpro = self.fred.get_series('INDPRO')
        cpi = self.fred.get_series('CPIAUCSL')
        yield_curve = self.fred.get_series('T10Y2Y')
        
        df = pd.DataFrame({'Growth': indpro, 'Inflation': cpi, 'Yield_Curve': yield_curve})
        self.macro_data = df.resample('ME').last().shift(1).dropna()

    def fetch_market_data(self):
        print("Fetching Market Data from Yahoo Finance...")
        prices = yf.download(self.tickers, start="2006-02-01", interval="1mo")['Close']
        prices.index = pd.to_datetime(prices.index).tz_localize(None)
        self.market_data = prices.resample('ME').last()

    def generate_signals(self):
        print("Processing Signals and Classifying Regimes...")
        df = self.macro_data.copy()
        
        df_yoy = df[['Growth', 'Inflation']].pct_change(12) * 100
        df_sma = df_yoy.rolling(window=6).mean()
        momentum = (df_yoy - df_sma).dropna()
        
        yc_sma = df['Yield_Curve'].rolling(window=6).mean()
        liq_momentum = (df['Yield_Curve'] - yc_sma).dropna()
        
        signals = momentum.join(liq_momentum.rename('Liq_Momentum'), how='inner')
        
        def classify(row):
            g, i, l = row['Growth'], row['Inflation'], row['Liq_Momentum']
            if g > 0 and i <= 0: regime = 'Goldilocks'
            elif g > 0 and i > 0: regime = 'Reflation'
            elif g <= 0 and i > 0: regime = 'Stagflation'
            else: regime = 'Deflation'
                
            liquidity = 'Easing' if l > 0 else 'Tightening'
            return pd.Series([regime, liquidity, f"{regime} & {liquidity}"])
            
        signals[['Regime', 'Liquidity', '3D_Regime']] = signals.apply(classify, axis=1)
        self.macro_data = signals

    def run_backtest(self):
        print("Running historical backtest...")
        returns = self.market_data.pct_change() * 100
        fwd_returns = returns.shift(-1).dropna()
        fwd_returns.columns = [f"{col}_Fwd_Return" for col in fwd_returns.columns]
        
        bt = self.macro_data[['Regime']].join(fwd_returns, how='inner').dropna()
        
        def select_asset(row):
            reg = row['Regime']
            if reg == 'Goldilocks': return row['SPY_Fwd_Return']
            elif reg == 'Reflation': return row['DBC_Fwd_Return']
            elif reg == 'Stagflation': return row['GLD_Fwd_Return']
            elif reg == 'Deflation': return row['TLT_Fwd_Return']
            return 0.0
            
        bt['Strategy_Return'] = bt.apply(select_asset, axis=1)
        bt['Strategy_Equity'] = 100 * (1 + bt['Strategy_Return'] / 100).cumprod()
        bt['SPY_Equity'] = 100 * (1 + bt['SPY_Fwd_Return'] / 100).cumprod()
        
        self.backtest_data = bt

    def print_performance(self):
        bt = self.backtest_data
        years = len(bt) / 12
        
        def calc_metrics(equity_col, return_col):
            cagr = (bt[equity_col].iloc[-1] / 100) ** (1 / years) - 1
            vol = (bt[return_col] / 100).std() * np.sqrt(12)
            sharpe = cagr / vol
            mdd = ((bt[equity_col] - bt[equity_col].cummax()) / bt[equity_col].cummax()).min()
            return cagr, vol, sharpe, mdd

        spy_metrics = calc_metrics('SPY_Equity', 'SPY_Fwd_Return')
        strat_metrics = calc_metrics('Strategy_Equity', 'Strategy_Return')
        
        print("\n=== Strategy Performance vs. S&P 500 (SPY) ===")
        print(f"{'Metric':<15} | {'S&P 500':<10} | {'Macro Strategy':<15}")
        print("-" * 45)
        print(f"{'CAGR':<15} | {spy_metrics[0]*100:>8.2f}% | {strat_metrics[0]*100:>13.2f}%")
        print(f"{'Volatility':<15} | {spy_metrics[1]*100:>8.2f}% | {strat_metrics[1]*100:>13.2f}%")
        print(f"{'Sharpe Ratio':<15} | {spy_metrics[2]:>8.2f}  | {strat_metrics[2]:>13.2f}")
        print(f"{'Max Drawdown':<15} | {spy_metrics[3]*100:>8.2f}% | {strat_metrics[3]*100:>13.2f}%")

    def plot_regimes(self):
        """Generates the interactive regime visualization with shaded backgrounds."""
        print("Generating Regime Chart...")
        
        # THE FIX: Find the overlapping dates between the two datasets
        common_dates = self.macro_data.index.intersection(self.market_data.index)
        
        # Filter both datasets to only use those overlapping dates
        plot_macro = self.macro_data.loc[common_dates]
        prices = self.market_data[self.tickers].loc[common_dates]
        
        normalized_prices = (prices / prices.iloc[0]) * 100
        
        regime_colors = {'Goldilocks': 'lightgreen', 'Reflation': 'orange', 'Stagflation': 'lightcoral', 'Deflation': 'lightblue'}
        fig = go.Figure()
        
        max_price = normalized_prices.max().max() * 1.15
        
        # Add background shading using the filtered dates
        for regime, color in regime_colors.items():
            y_vals = [5000 if r == regime else 0 for r in plot_macro['Regime']]
            fig.add_trace(go.Scatter(x=plot_macro.index, y=y_vals, fill='tozeroy', mode='none', fillcolor=color, opacity=0.3, name=f"Regime: {regime}", hoverinfo='skip', line_shape='hv'))
        
        # Add Asset Lines
        colors = {'SPY': 'black', 'TLT': 'blue', 'GLD': 'gold', 'DBC': 'brown'}
        for ticker in self.tickers:
            fig.add_trace(go.Scatter(x=normalized_prices.index, y=normalized_prices[ticker], mode='lines', name=ticker, line=dict(color=colors[ticker], width=2)))
            
        # Highlight Key Events
        key_events = [{"date": "2008-09-30", "text": "Lehman Collapse<br>(Deflation)"}, {"date": "2020-03-31", "text": "COVID Crash<br>(Deflation)"}, {"date": "2022-03-31", "text": "Fed Rate Hikes<br>(Stagflation)"}]
        
        for event in key_events:
            try: y_loc = normalized_prices.loc[event["date"], 'SPY']
            except KeyError: y_loc = 100
            fig.add_annotation(x=event["date"], y=y_loc, text=event["text"], showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, ax=-40, ay=-60, bgcolor="white", bordercolor="black", borderwidth=1, opacity=0.8)

        fig.update_layout(title='Interactive Macro Regime Tracker (Toggleable)', yaxis_title='Growth of $100 Initial Investment', xaxis_title='Date', hovermode='x unified', template='plotly_white', height=700, yaxis=dict(range=[0, max_price]))
        
        fig.write_html("regime_chart.html", auto_open=True)

    def plot_equity_curve(self):
        """Generates the backtest equity curve chart."""
        print("Generating Equity Curve Chart...")
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(x=self.backtest_data.index, y=self.backtest_data['Strategy_Equity'], mode='lines', name='Macro Regime Strategy', line=dict(color='darkblue', width=3)))
        fig.add_trace(go.Scatter(x=self.backtest_data.index, y=self.backtest_data['SPY_Equity'], mode='lines', name='Benchmark: S&P 500 (SPY)', line=dict(color='gray', width=2, dash='dash')))
        
        fig.update_layout(title='Strategy Backtest: Macro Regime Rotation vs. Buy-and-Hold', yaxis_title='Portfolio Value ($)', xaxis_title='Date', hovermode='x unified', template='plotly_white', height=600)
        
        fig.write_html("equity_curve_chart.html", auto_open=True)

# ==========================================
# EXECUTION BLOCK
# ==========================================
if __name__ == "__main__":
    # Insert your FRED API key here! Keep the quotation marks!
    API_KEY = "69cc0da9e248e5739ce02131a8151e89"
    
    tracker = MacroRegimeTracker(fred_api_key=API_KEY)
    
    tracker.fetch_macro_data()
    tracker.fetch_market_data()
    tracker.generate_signals()
    tracker.run_backtest()
    tracker.print_performance()
    
    tracker.plot_regimes()
    tracker.plot_equity_curve()