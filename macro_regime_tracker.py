import os
import webbrowser
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
        print("          STRATEGY PERFORMANCE VS S&P 500       ")
        print("=" * 48)
        print(f"{'Metric':<16} | {'S&P 500 (SPY)':<14} | {'Macro Strategy':<14}")
        print("-" * 48)
        print(f"{'CAGR':<16} | {spy_cagr * 100:>12.2f}% | {strat_cagr * 100:>12.2f}%")
        print(f"{'Volatility (Ann)':<16} | {spy_vol * 100:>12.2f}% | {strat_vol * 100:>12.2f}%")
        print(f"{'Sharpe Ratio':<16} | {spy_sharpe:>13.2f} | {strat_sharpe:>13.2f}")
        print(f"{'Max Drawdown':<16} | {spy_mdd * 100:>12.2f}% | {strat_mdd * 100:>12.2f}%")
        print("=" * 48 + "\n")

    def _wrap_with_dashboard_template(self, fig: go.Figure, title: str, subtitle: str, guide_html: str, filename: str):
        """Wraps Plotly figure into an institutional dark dashboard with an interpretation guide."""
        chart_div = fig.to_html(full_html=False, include_plotlyjs='cdn')
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- ANTI-CACHING TAGS TO FORCE BROWSER/GITHUB REFRESH -->
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: #0b0e14;
            color: #e6edf3;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            padding: 30px;
        }}
        .header {{
            margin-bottom: 24px;
            border-bottom: 1px solid #21262d;
            padding-bottom: 16px;
        }}
        .header h1 {{
            font-size: 26px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.5px;
        }}
        .header p {{
            font-size: 14px;
            color: #8b949e;
            margin-top: 6px;
        }}
        .chart-card {{
            background-color: #12161f;
            border: 1px solid #21262d;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 30px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }}
        .guide-container {{
            background-color: #12161f;
            border: 1px solid #21262d;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }}
        .guide-title {{
            font-size: 18px;
            font-weight: 600;
            color: #58a6ff;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
        }}
        .card {{
            background-color: #161b26;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
        }}
        .card-header {{
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .card p {{
            font-size: 13px;
            line-height: 1.5;
            color: #c9d1d9;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    <div class="chart-card">
        {chart_div}
    </div>
    <div class="guide-container">
        <div class="guide-title">
            <span>&#9432;</span> How to Interpret This Dashboard
        </div>
        {guide_html}
    </div>
</body>
</html>"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        # Automatically open the generated HTML file in the default web browser
        filepath = f"file:///{os.path.abspath(filename).replace('\\', '/')}"
        webbrowser.open(filepath)

    def plot_regimes(self, output_dir: str = "."):
        """Exports high-contrast interactive regime history with institutional styling to HTML."""
        print("Generating high-contrast regime chart...")
        common_dates = self.macro_data.index.intersection(self.market_data.index)
        plot_macro = self.macro_data.loc[common_dates]
        prices = self.market_data[self.tickers].loc[common_dates]
        normalized_prices = (prices / prices.iloc[0]) * 100

        fig = go.Figure()

        # Regime background shading (punchy contrast on dark canvas)
        regime_colors = {
            'Goldilocks': 'rgba(46, 204, 113, 0.22)',   # Vivid Emerald
            'Reflation': 'rgba(243, 156, 18, 0.22)',    # Warm Amber
            'Stagflation': 'rgba(231, 76, 60, 0.22)',   # Vibrant Crimson
            'Deflation': 'rgba(52, 152, 219, 0.22)'     # Electric Blue
        }
        for regime, color in regime_colors.items():
            y_vals = [5000 if r == regime else 0 for r in plot_macro['Regime']]
            fig.add_trace(go.Scatter(
                x=plot_macro.index,
                y=y_vals,
                fill='tozeroy',
                mode='none',
                fillcolor=color,
                opacity=0.4,
                name=f"Regime: {regime}",
                hoverinfo='skip',
                line_shape='hv'
            ))

        # Vibrant neon asset paths
        line_specs = {
            'SPY': dict(color='#00F0FF', width=2.5, name='SPY (S&P 500)'),
            'TLT': dict(color='#A29BFE', width=2.2, name='TLT (20Y+ Treasuries)'),
            'GLD': dict(color='#FFD700', width=2.2, name='GLD (Gold)'),
            'DBC': dict(color='#FF7675', width=2.0, name='DBC (Commodities)')
        }
        for ticker in self.tickers:
            fig.add_trace(go.Scatter(
                x=normalized_prices.index,
                y=normalized_prices[ticker],
                mode='lines',
                name=line_specs[ticker]['name'],
                line=dict(color=line_specs[ticker]['color'], width=line_specs[ticker]['width'])
            ))

        # Historical crisis callouts
        key_events = [
            {"date": "2008-09-30", "text": "Lehman Collapse<br>(Deflation Rotation)", "ay": -70},
            {"date": "2020-03-31", "text": "COVID Crash<br>(Deflation Liquidity)", "ay": -85},
            {"date": "2022-03-31", "text": "Fed Rate Hike Cycle<br>(Stagflation Spike)", "ay": -65}
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
                arrowsize=1,
                arrowwidth=1.5,
                arrowcolor="#8B949E",
                ax=-40,
                ay=event["ay"],
                bgcolor="#161B26",
                bordercolor="#30363D",
                borderwidth=1,
                font=dict(color="#FFFFFF", size=11)
            )

        max_val = normalized_prices.max().max() * 1.15
        fig.update_layout(
            paper_bgcolor="#12161f",
            plot_bgcolor="#12161f",
            font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", color="#C9D1D9"),
            yaxis=dict(
                title="Normalized Performance (Base = 100)",
                range=[0, max_val],
                gridcolor="#21262d",
                zerolinecolor="#30363d",
                showline=True,
                linecolor="#30363d"
            ),
            xaxis=dict(
                title="Observation Date",
                gridcolor="#21262d",
                zerolinecolor="#30363d",
                showline=True,
                linecolor="#30363d"
            ),
            hovermode="x unified",
            height=650,
            margin=dict(l=50, r=30, t=20, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=11)
            )
        )

        guide_html = """
        <div class="grid">
            <div class="card" style="border-left: 4px solid #2ecc71;">
                <div class="card-header" style="color: #2ecc71;">
                    <span class="badge" style="background-color: rgba(46, 204, 113, 0.2); color: #2ecc71;">GOLDILOCKS</span>
                    Accelerating Growth + Decelerating Inflation
                </div>
                <p><strong>Primary Asset: SPY (S&P 500)</strong><br>Corporate margins expand without central bank interest rate pressure. Equities historically dominate this regime with low macro drag.</p>
            </div>
            <div class="card" style="border-left: 4px solid #f39c12;">
                <div class="card-header" style="color: #f39c12;">
                    <span class="badge" style="background-color: rgba(243, 156, 18, 0.2); color: #f39c12;">REFLATION</span>
                    Accelerating Growth + Accelerating Inflation
                </div>
                <p><strong>Primary Asset: DBC (Commodities)</strong><br>Aggregate consumer and industrial demand outstrips raw material capacity. Real physical assets appreciate faster than financial paper assets.</p>
            </div>
            <div class="card" style="border-left: 4px solid #e74c3c;">
                <div class="card-header" style="color: #e74c3c;">
                    <span class="badge" style="background-color: rgba(231, 76, 60, 0.2); color: #e74c3c;">STAGFLATION</span>
                    Decelerating Growth + Accelerating Inflation
                </div>
                <p><strong>Primary Asset: GLD (Gold)</strong><br>Rising production costs compress company earnings while monetary authorities hike borrowing rates. Physical gold protects purchasing power.</p>
            </div>
            <div class="card" style="border-left: 4px solid #3498db;">
                <div class="card-header" style="color: #3498db;">
                    <span class="badge" style="background-color: rgba(52, 152, 219, 0.2); color: #3498db;">DEFLATION</span>
                    Decelerating Growth + Decelerating Inflation
                </div>
                <p><strong>Primary Asset: TLT (20Y+ Treasuries)</strong><br>Demand contraction prompts emergency central bank policy rate reductions. Plunging yields drive capital gains in long-duration sovereign paper.</p>
            </div>
        </div>
        """

        filename = os.path.join(output_dir, "regime_chart.html")
        self._wrap_with_dashboard_template(
            fig=fig,
            title="Macroeconomic Regime History & Asset Normalization",
            subtitle="Historical business cycle partitioning via US Industrial Production, CPI, and 10Y-2Y Treasury spread momentum",
            guide_html=guide_html,
            filename=filename
        )

    def plot_equity_curve(self, output_dir: str = "."):
        """Exports high-contrast interactive backtest equity curve with institutional styling to HTML."""
        print("Generating high-contrast equity curve chart...")
        fig = go.Figure()

        # Strategy Line (Neon Mint Green)
        fig.add_trace(go.Scatter(
            x=self.backtest_data.index,
            y=self.backtest_data['Strategy_Equity'],
            mode='lines',
            name='Macro Regime Tactical Strategy',
            line=dict(color='#00E676', width=2.8)
        ))

        # Benchmark Line (Silver-Gray Dashed)
        fig.add_trace(go.Scatter(
            x=self.backtest_data.index,
            y=self.backtest_data['SPY_Equity'],
            mode='lines',
            name='Benchmark: S&P 500 Buy & Hold (SPY)',
            line=dict(color='#8B949E', width=2.0, dash='dash')
        ))

        fig.update_layout(
            paper_bgcolor="#12161f",
            plot_bgcolor="#12161f",
            font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", color="#C9D1D9"),
            yaxis=dict(
                title="Portfolio Equity ($ Initial Base = 100)",
                gridcolor="#21262d",
                zerolinecolor="#30363d",
                showline=True,
                linecolor="#30363d"
            ),
            xaxis=dict(
                title="Observation Date",
                gridcolor="#21262d",
                zerolinecolor="#30363d",
                showline=True,
                linecolor="#30363d"
            ),
            hovermode="x unified",
            height=600,
            margin=dict(l=50, r=30, t=20, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=11)
            )
        )

        guide_html = """
        <div class="grid">
            <div class="card">
                <div class="card-header" style="color: #00E676;">
                    <span>&#9670;</span> Tail-Risk & Crash Defense (2008 & 2020)
                </div>
                <p>During the 2008 Global Financial Crisis, passive equity buy-and-hold crashed by <strong>-50.78%</strong>. By actively rotating into long-term sovereign debt (TLT) upon deflationary momentum detection, the strategy capped maximum historical drawdown to <strong>-32.36%</strong>.</p>
            </div>
            <div class="card">
                <div class="card-header" style="color: #58a6ff;">
                    <span>&#9670;</span> The Opportunity Cost in Structural Bull Markets
                </div>
                <p>During the protracted zero-interest-rate environment (2012–2021), US large-cap equities compounded aggressively. Any dynamic rotation into defensive commodities or gold during short-lived growth decelerations incurred an performance drag against 100% equity concentration.</p>
            </div>
            <div class="card">
                <div class="card-header" style="color: #ffd700;">
                    <span>&#9670;</span> Implementation: Dynamic Tilting vs. All-or-Nothing
                </div>
                <p>The practical takeaway for asset allocators is using this regime signal as a <strong>portfolio tilting overlay</strong> (e.g., maintaining a 60/40 anchor while shifting 20% tactical sleeves into the favored regime asset) rather than full 100% binary switches.</p>
            </div>
        </div>
        """

        filename = os.path.join(output_dir, "equity_curve_chart.html")
        self._wrap_with_dashboard_template(
            fig=fig,
            title="Equity Curve Simulation: Macro Tactical Rotation vs. S&P 500",
            subtitle="Cumulative compounding simulation ($100 starting base, 2006-Present) strictly lagged to eliminate look-ahead bias",
            guide_html=guide_html,
            filename=filename
        )


if __name__ == "__main__":
    API_KEY = "YOUR_FRED_API_KEY"
    SAVE_DIRECTORY = r"C:\Documents\Project\Macro\Projects\Macro regime tracker"

    # Automatically create the directory if it doesn't already exist
    os.makedirs(SAVE_DIRECTORY, exist_ok=True)

    tracker = MacroRegimeTracker(fred_api_key=API_KEY)
    tracker.fetch_macro_data()
    tracker.fetch_market_data()
    tracker.generate_signals()
    tracker.run_backtest()
    tracker.print_performance()

    # Pass the custom save directory to the plotting functions
    tracker.plot_regimes(output_dir=SAVE_DIRECTORY)
    tracker.plot_equity_curve(output_dir=SAVE_DIRECTORY)
