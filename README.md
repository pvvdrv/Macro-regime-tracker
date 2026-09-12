# Quantitative Macro Regime Tracker: A Rule-Based Asset Allocation Engine

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![Plotly](https://img.shields.io/badge/Plotly-Interactive%20Charts-indigo?logo=plotly)
![FRED](https://img.shields.io/badge/Data-FRED%20API-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

A systematic macroeconomic classification engine and backtesting pipeline written in Object-Oriented Python. The tracker evaluates second-derivative momentum across Growth, Inflation, and Treasury Yield Curve liquidity to categorize economic environments into discrete regimes and simulate dynamic asset rotation strategies.

---

## 📊 Live Interactive Dashboards
Hosted live via GitHub Pages (no code execution or API keys required):

* 🌐 **[Interactive Regime History & Asset Normalization Chart](https://pvvdrv.github.io/Macro-regime-tracker/regime_chart.html)**
* 📈 **[Dynamic Strategy vs. S&P 500 Compounding Equity Curve](https://pvvdrv.github.io/Macro-regime-tracker/equity_curve_chart.html)**

---

## 1. Executive Summary & Project Objective
In traditional portfolio management, asset allocation decisions are frequently steered by discretionary narratives or static "60/40" assumptions. This project builds a programmatic, rule-based quantitative engine that eliminates human bias by systematically mapping the U.S. macroeconomic cycle into defined regimes.

The core research question investigated is:
> *Can an algorithmic strategy dynamically rotate 100% of capital into the theoretically optimal asset class for each economic regime to preserve capital and enhance risk-adjusted returns relative to a passive Buy-and-Hold S&P 500 benchmark?*

The system features:
1. Automated macroeconomic ingestion via the Federal Reserve Economic Data (FRED) API.
2. Market price scraping across core asset classes via Yahoo Finance.
3. Second-derivative momentum calculation using rolling Simple Moving Averages.
4. Publication lag adjustments to eliminate look-ahead bias.
5. Historical backtest simulation with CAGR, Volatility, Sharpe Ratio, and Maximum Drawdown analysis.
6. Interactive HTML visualizations exported via Plotly.

---

## 2. Core Macroeconomic Variables

The model relies on three macroeconomic proxies representing production, consumer pricing, and systemic liquidity:

* **Growth — Industrial Production Index (`INDPRO`):**
  Measures the real physical output of manufacturing, mining, and electric/gas utilities across the United States. Unlike quarterly Gross Domestic Product (GDP), Industrial Production is published monthly, providing a faster, higher-frequency coincident indicator of the physical business cycle.
* **Inflation — Consumer Price Index for All Urban Consumers (`CPIAUCSL`):**
  Tracks price changes in a representative basket of goods and services purchased by households. It measures purchasing power degradation and dictates the central bank's monetary reaction function.
* **Liquidity & Financial Conditions — 10-Year Minus 2-Year Treasury Spread (`T10Y2Y`):**
  The slope of the Treasury yield curve serves as a market-driven barometer of credit availability and monetary tightness. A steepening curve reflects easing financial conditions and capital willingness to take duration risk; a flattening or inverted curve signals restrictive monetary policy and impending credit contraction.

---

## 3. Mathematical Framework & Signal Processing

### Second-Derivative Momentum Logic
Financial asset prices do not trade on static macroeconomic levels; they reprice on the **rate of change (first derivative)** and the **acceleration/deceleration (second derivative)** relative to expectations. 

To model this quantitatively:
1. **Year-over-Year (YoY) Base:** The model computes the 12-month percentage change to strip away seasonal anomalies (e.g., retail inventory surges in Q4).
2. **Trendline Extraction:** A 6-month Simple Moving Average (SMA) of that YoY rate is calculated to establish the baseline economic trend.
3. **Momentum Spread:** Economic momentum is defined as the current YoY change minus its 6-month trendline:

$$\Delta X_t = X_t - \text{SMA}_6(X_t)$$

* If $\Delta X_t > 0$: The macroeconomic metric is **accelerating** relative to its medium-term trend.
* If $\Delta X_t \le 0$: The macroeconomic metric is **decelerating** relative to its medium-term trend.

### Yield Curve Liquidity Overlay
For the Treasury spread, the model calculates momentum directly as the spread minus its 6-month SMA:
* $\Delta \text{Spread}_t > 0 \rightarrow$ **Easing Liquidity**
* $\Delta \text{Spread}_t \le 0 \rightarrow$ **Tightening Liquidity**

### Look-Ahead Bias Mitigation
A widespread flaw in retail quantitative modeling is look-ahead bias—assuming economic data is available immediately on the last day of the reference month. In reality, macroeconomic indicators operate with substantial publication delays (e.g., January CPI is not published until mid-February). 

To preserve backtest integrity, the pipeline implements a strict **1-month forward shift (`.shift(1)`)** on all raw macroeconomic series. This ensures trades are executed solely on information that was verifiably available to market participants.

---

## 4. The Macro Allocation Matrix

The engine combines Growth momentum ($\Delta G$) and Inflation momentum ($\Delta I$) into a 4-quadrant state space. At the end of each month, 100% of the portfolio is allocated to the historically favored ETF for the prevailing regime:

| Regime | Growth ($\Delta G$) | Inflation ($\Delta I$) | Target Asset | ETF Ticker | Economic Transmission Mechanism |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Goldilocks** | Accelerating ($>0$) | Decelerating ($\le0$) | U.S. Equities | **SPY** | Expanding corporate margins, steady top-line growth, and absent discount rate pressure. |
| **Reflation** | Accelerating ($>0$) | Accelerating ($>0$) | Commodities | **DBC** | Strong demand pulls raw material prices upward; producers pass costs downstream. |
| **Stagflation** | Decelerating ($\le0$) | Accelerating ($>0$) | Physical Gold | **GLD** | Negative supply shocks, profit margin compression, and fiat currency debasement. |
| **Deflation** | Decelerating ($\le0$) | Decelerating ($\le0$) | Long-Term Treasuries | **TLT** | Aggregate demand destruction; central banks cut policy rates, driving bond price appreciation via duration. |

---

## 5. Backtest Simulation & Quantitative Performance

### Backtest Mechanics
* **Evaluation Horizon:** February 2006 to Present (inception constraint imposed by `DBC`).
* **Forward Trade Execution:** Monthly signals generated at $T$ capture returns over $T+1$ via shifted return matrices (`.shift(-1)`).
* **Compounding Model:** Portfolio values are simulated through discrete compounding:

$$V_t = V_0 \times \prod_{i=1}^{t} \left(1 + \frac{R_i}{100}\right)$$

### Performance Metrics Autopsy (2006 – Present)

| Metric | Benchmark: S&P 500 (`SPY`) | Macro Regime Strategy | Delta / Quant Takeaway |
| :--- | :---: | :---: | :--- |
| **CAGR** | 11.11% | 6.03% | Underperformance driven by non-equity drag during extended bull markets. |
| **Annualized Volatility** | 15.13% | 15.97% | Comparable overall risk profile across structural cycles. |
| **Sharpe Ratio** ($R_f = 0$) | 0.73 | 0.38 | Drag from holding defensive assets during the post-2008 QE regime. |
| **Maximum Drawdown (MDD)** | **-50.78%** | **-32.36%** | **+18.42% Capital Preservation during systemic collapse (2008).** |

### Key Analytical Findings
1. **The Equity Risk Premium Drag:** Between 2009 and 2021, global markets experienced an unprecedented Zero Interest Rate Policy (ZIRP) and Quantitative Easing (QE) regime. The equity risk premium overwhelmed all traditional asset classes. Holding defensive assets (Bonds, Gold, Commodities) during false recession signals resulted in significant opportunity costs relative to equities.
2. **Superior Capital Preservation:** The primary virtue of the model is downside asymmetry. During the 2008 Global Financial Crisis, the passive S&P 500 crashed by **-50.78%**. The regime engine detected the deflationary impulse and systematically rotated into Long Treasuries (`TLT`), capping the portfolio's maximum historical drawdown at **-32.36%**.
3. **The Tilting Takeaway:** Binary 100% capital rotation models are structurally vulnerable to whipsaw costs. However, this engine establishes that macroeconomic regime classification provides strong risk-off protection. The institutional next step is using this tracker as a **portfolio tilting overlay** (e.g., adjusting an equity/bond baseline between 80/20 and 40/60) rather than an all-or-nothing switch.

---

## 6. Repository Architecture

```text
Macro-regime-tracker/
│
├── macro_regime_tracker.py   # Complete Object-Oriented pipeline (Classes: ETL, Signal, Backtest, Plots)
├── regime_chart.html         # Output dashboard: Regime background shading vs. normalized asset paths
├── equity_curve_chart.html   # Output dashboard: Cumulative strategy returns vs. SPY benchmark
└── README.md                 # Project documentation and quantitative research summary
