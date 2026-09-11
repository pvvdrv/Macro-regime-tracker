# Quantitative Macro Regime Tracker

## 1. Project Overview
This project is a systematic, rule-based macroeconomic regime tracker. In traditional finance, discretionary portfolio managers often rely on subjective interpretations of economic data to adjust their asset allocations. This project removes human bias by using quantitative matrix operations in Python to classify the U.S. economy into distinct "regimes" based on the momentum of Growth, Inflation, and Liquidity. 

The core objective is to backtest whether dynamically rotating capital into theoretically optimal asset classes based on these quantitative regimes can improve risk-adjusted returns and reduce maximum drawdowns compared to a passive S&P 500 benchmark.

## 2. Core Economic Variables
The model relies on three fundamental macroeconomic proxies, sourced directly via the Federal Reserve Economic Data (FRED) API.

* **Growth (INDPRO):** The U.S. Industrial Production Index is used as the proxy for economic output. It is highly sensitive to the physical business cycle, making it a faster coincident indicator than quarterly GDP.
* **Inflation (CPIAUCSL):** The Consumer Price Index represents the purchasing power of the consumer and dictates the tightening or easing pressure placed on the central bank.
* **Liquidity / Interest Rates (T10Y2Y):** The spread between the 10-Year and 2-Year Treasury yields serves as a proxy for financial conditions. An expanding (steepening) spread indicates easing liquidity, while a shrinking or inverted (flattening) spread signals restrictive credit conditions.

## 3. Methodology & Signal Processing
Financial markets do not price in absolute economic numbers; they price in the *rate of change* relative to expectations. Therefore, the model processes the raw economic data through a second-derivative momentum framework.

### Momentum Calculation
To strip out seasonal volatility, the model calculates the Year-over-Year (YoY) percentage change for Growth and Inflation. It then calculates a 6-month Simple Moving Average (SMA) of that YoY rate to establish a baseline trend. 

Momentum is defined as the current YoY rate minus its 6-month trend:
$$ \Delta X_t = X_t - \text{SMA}_6(X_t) $$

If the result is positive, the metric is accelerating. If negative, the metric is decelerating.

### Preventing Look-Ahead Bias
A critical flaw in many retail quantitative models is look-ahead bias—trading on economic data on the day it represents, rather than the day it was published. To ensure the integrity of the historical backtest, this model applies a strict 1-month lag to all macroeconomic data, ensuring the algorithm only executes trades using fully public information.

## 4. The Macroeconomic Matrix (Regime Classification)
By combining the momentum of Growth and Inflation, the algorithm classifies every month into one of four classic economic quadrants. It then allocates 100% of the portfolio into the historically favored Exchange Traded Fund (ETF) for that specific environment.

* **Goldilocks (Accelerating Growth, Decelerating Inflation):** The optimal environment for corporate earnings. Risk assets are favored. **Allocation:** S&P 500 Equities (SPY).
* **Reflation (Accelerating Growth, Accelerating Inflation):** The economy is overheating, and raw material demand outstrips supply. **Allocation:** Broad Commodities (DBC).
* **Stagflation (Decelerating Growth, Accelerating Inflation):** The most destructive environment for traditional 60/40 portfolios. Corporate margins are squeezed, and central banks are forced to hike rates into a slowing economy. **Allocation:** Gold (GLD).
* **Deflation (Decelerating Growth, Decelerating Inflation):** A recessionary impulse characterized by demand destruction. Central banks cut rates to zero, making existing high-yielding debt highly valuable. **Allocation:** Long-Duration U.S. Treasuries (TLT).

## 5. Backtest Results & Conclusions
The strategy was backtested on monthly data from February 2006 to the present day, tracking the compounding equity curve of a dynamic portfolio against a passive Buy-and-Hold S&P 500 strategy.

* **The Equity Risk Premium Challenge:** From 2009 to 2021, global markets experienced an unprecedented era of Zero Interest Rate Policy (ZIRP) and Quantitative Easing. During this period, the equity risk premium was so massive that any time the model rotated out of Equities and into defensive assets, it suffered a performance drag relative to the raging bull market.
* **Superior Drawdown Protection:** The true value of the regime tracker is revealed during systemic crises. During the 2008 Global Financial Crisis, the S&P 500 suffered a catastrophic maximum drawdown of over 50%. By systematically identifying the shift into Deflation and rotating into long-duration bonds, the macro strategy capped its worst historical drawdown at approximately 32%.
* **Conclusion:** The model proves that a rule-based macroeconomic framework can successfully navigate systemic shocks. While a binary "100% rotation" strategy sacrifices too much upside during prolonged bull markets, this quantitative engine serves as an excellent foundation for an institutional "portfolio tilting" strategy.

## 6. Future Enhancements
To evolve this model from a discrete rule-based tracker into a predictive quantitative engine, the following upgrades are planned:
* **Machine Learning Integration:** Replacing the moving average crossover logic with a Random Forest classifier to predict the probability of a regime transition *before* the lagged economic data is officially published.
* **Continuous-Time Yield Curve Modeling:** Expanding the liquidity overlay to model absolute real rates alongside the 10Y/2Y spread, providing a more granular signal for bond allocation.
* **Portfolio Tilting:** Shifting from a 100% capital rotation to a dynamic weighting model (e.g., tilting a baseline 60/40 portfolio based on the active regime's risk profile).

## 7. How to Run This Project
### Prerequisites
* Python 3.8+
* A free API key from [FRED (Federal Reserve Economic Data)](https://fred.stlouisfed.org/)

### Installation
1. Clone this repository to your local machine.
2. Install the required dependencies:
   ```bash
   pip install pandas numpy yfinance fredapi plotly