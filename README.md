# Quantitative Macro Regime Tracker

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![Plotly](https://img.shields.io/badge/Plotly-Interactive%20Charts-indigo?logo=plotly)
![Data](https://img.shields.io/badge/Data-FRED%20API-green)

A rule-based macroeconomic classification engine and systematic asset allocation model. The engine tracks the second-derivative momentum of Growth, Inflation, and Yield Curve liquidity to rotate across asset classes and mitigate systemic drawdowns.

---

## 📊 Live Interactive Visualizations
Explore the interactive charts generated directly by the model (hosted via GitHub Pages):

* **[Interactive Regime History & Asset Trajectories](https://pvvdrv.github.io/Macro-regime-tracker/regime_chart.html)**
* **[Dynamic Strategy vs. S&P 500 Equity Curve](https://pvvdrv.github.io/Macro-regime-tracker/equity_curve_chart.html)**

---

## 1. Quantitative Framework

### Momentum & Signal Extraction
Financial markets reprice assets on the *acceleration or deceleration* of economic trends, rather than static levels. The model calculates the Year-over-Year (YoY) percentage change for Industrial Production (Growth) and CPI (Inflation), benchmarked against a 6-month Simple Moving Average (SMA):

$$\Delta X_t = X_t - \text{SMA}_6(X_t)$$

* $\Delta X_t > 0$: Economic variable is **accelerating**.
* $\Delta X_t \le 0$: Economic variable is **decelerating**.

### Look-Ahead Bias Mitigation
Macroeconomic statistics are subject to publication reporting delays. To maintain backtest validity, a strict **1-month publication lag** (`shift(1)`) is enforced across all FRED series.

---

## 2. Macro Allocation Matrix

| Regime | Growth ($\Delta G$) | Inflation ($\Delta I$) | Primary Allocation | Economic Rationale |
| :--- | :---: | :---: | :---: | :--- |
| **Goldilocks** | > 0 | $\le$ 0 | **SPY** (S&P 500) | Expanding earnings + loose financial conditions |
| **Reflation** | > 0 | > 0 | **DBC** (Commodities) | Demand pull and input-cost acceleration |
| **Stagflation**| $\le$ 0 | > 0 | **GLD** (Gold) | Margin compression and monetary debasement hedge |
| **Deflation** | $\le$ 0 | $\le$ 0 | **TLT** (Long Treasuries)| Demand destruction and flight-to-safety duration |

*A 10Y-2Y Treasury spread momentum overlay provides secondary liquidity confirmation (Easing vs. Tightening).*

---

## 3. Backtest Performance (2006 – Present)

| Metric | Benchmark: S&P 500 (SPY) | Macro Regime Strategy | Delta / Insight |
| :--- | :---: | :---: | :--- |
| **CAGR** | 11.11% | 6.03% | SPY benefited from the post-2008 zero-rate regime |
| **Volatility (Ann.)**| 15.13% | 15.97% | Comparable risk profile across cycles |
| **Sharpe Ratio** | 0.73 | 0.38 | Drag from holding defensive assets in bull markets |
| **Max Drawdown** | **-50.78%** | **-32.36%** | **+18.42% capital preservation in crises (2008)** |

---

## 4. Repository Structure

```text
├── macro_regime_tracker.py   # Full OOP pipeline (Data, Signals, Backtest, Plots)
├── regime_chart.html         # Exported interactive regime dashboard
├── equity_curve_chart.html   # Exported backtest equity curve
└── README.md                 # Project documentation and performance summary
