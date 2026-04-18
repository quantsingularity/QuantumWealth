# AI Models Documentation

This document describes the mathematical foundations, implementation choices, and configuration of each AI and ML module in `code/ai_models/`.

---

## Portfolio Optimizer

**Module:** `ai_models.portfolio_optimizer.optimizer`  
**Class:** `PortfolioOptimizer`

### Strategies

#### Mean-Variance Optimization (Markowitz 1952)

Minimizes portfolio variance for a given expected return, or maximizes the Sharpe ratio proxy when no target return is specified.

Objective (target return mode):

```
minimize    w^T * Sigma * w
subject to  sum(w) = 1
            mu^T * w >= target_return
            min_weight <= w_i <= max_weight
```

Objective (Sharpe proxy mode):

```
maximize    mu^T * w - 0.5 * w^T * Sigma * w
subject to  sum(w) = 1
            min_weight <= w_i <= max_weight
```

Solver: ECOS via CVXPY.

| Parameter     | Default | Description                                   |
| ------------- | ------- | --------------------------------------------- |
| max_weight    | 0.40    | Maximum single position weight                |
| min_weight    | 0.01    | Minimum non-zero position weight              |
| target_return | None    | Annual target, triggers minimum variance mode |

#### Black-Litterman (Black and Litterman 1992)

Blends market equilibrium returns with investor views using Bayesian updating.

Steps:

1. Compute market equilibrium returns: pi = lambda _ Sigma _ w_market
2. If views are provided, compute posterior: mu_BL = [(tau*Sigma)^-1 + P^T * Omega^-1 * P]^-1 \* [...]
3. Run mean-variance optimization on posterior expected returns.

| Parameter       | Default | Description                                                   |
| --------------- | ------- | ------------------------------------------------------------- |
| views           | None    | Dict of ticker to expected annual return, e.g. {"AAPL": 0.15} |
| view_confidence | 0.5     | Scales the view uncertainty matrix Omega                      |
| risk_aversion   | 3.0     | Lambda in equilibrium return formula                          |

#### Risk Parity / Equal Risk Contribution (Maillard 2010)

Each position contributes equally to total portfolio volatility.

Implemented as a convex approximation:

```
minimize    sqrt(w^T * Sigma * w) - (1/n) * sum(log(w_i))
subject to  sum(w) = 1
            0.005 <= w_i <= 0.50
```

The log-barrier term forces equal risk sharing without explicit risk contribution constraints.

#### Hierarchical Risk Parity (Lopez de Prado 2016)

Addresses the sensitivity of mean-variance optimization to estimation error by using hierarchical clustering instead of matrix inversion.

Steps:

1. Compute correlation-based distance matrix: d_ij = sqrt((1 - rho_ij) / 2)
2. Apply single-linkage hierarchical clustering.
3. Quasi-diagonalize the covariance matrix by sorting assets by cluster membership.
4. Allocate weights via recursive bisection: each cluster's weight is split proportionally to inverse cluster variance.

HRP does not require an invertible covariance matrix and is more robust to estimation error than Markowitz optimization.

### Efficient Frontier

The efficient frontier is computed by sweeping 30 target return values between the minimum and maximum asset expected returns and solving a minimum-variance problem at each point.

---

## Risk Engine

**Module:** `ai_models.risk_engine.engine`  
**Class:** `RiskEngine`

### Value at Risk (VaR)

Historical method:

```
VaR(alpha) = -Percentile(portfolio_returns, (1 - alpha) * 100)
```

Parametric method (assumes normal distribution):

```
VaR(alpha) = -(mu + sigma * z_alpha)
```

where z_alpha is the standard normal quantile at confidence level alpha.

Time scaling: VaR is scaled to horizon h days using the square-root-of-time rule:

```
VaR(h) = VaR(1) * sqrt(h)
```

### Conditional VaR (Expected Shortfall)

```
CVaR(alpha) = -E[R | R <= VaR(alpha)]
```

Computed as the mean of all returns that fall at or below the VaR threshold.

### Performance Metrics

| Metric        | Formula                                                  | Description                       |
| ------------- | -------------------------------------------------------- | --------------------------------- |
| Sharpe Ratio  | (R - Rf) / sigma                                         | Risk-adjusted return, Rf = 5%     |
| Sortino Ratio | (R - Rf) / sigma_down                                    | Uses only downside deviation      |
| Calmar Ratio  | R / MaxDD                                                | Return per unit of max drawdown   |
| Omega Ratio   | Sum(gains above threshold) / Sum(losses below threshold) | Gain-to-loss ratio                |
| Max Drawdown  | min((P_t - max(P_0..t)) / max(P_0..t))                   | Peak-to-trough percentage decline |

### Stress Test Scenarios

| Scenario              | Period                       | SPY Return | QQQ Return | TLT Return |
| --------------------- | ---------------------------- | ---------- | ---------- | ---------- |
| 2008 Financial Crisis | Sep 2008 to Mar 2009         | -56.5%     | -52.0%     | +33.0%     |
| COVID-19 Crash        | Feb 2020 to Mar 2020         | -34.0%     | -28.0%     | +18.0%     |
| Dot-Com Bust          | Mar 2000 to Oct 2002         | -49.0%     | -83.0%     | +20.0%     |
| Rate Shock            | 2022 rising rate environment | -15.0%     | -20.0%     | -25.0%     |
| Inflation Spike       | 1970s-style inflation surge  | -10.0%     | -18.0%     | -30.0%     |

Unknown tickers receive a default shock of -25% to be conservative.

### Monte Carlo Simulation

Uses Geometric Brownian Motion:

```
S(t+1) = S(t) * exp((mu - sigma^2/2) * dt + sigma * sqrt(dt) * Z)
```

where Z ~ N(0,1). Parameters mu and sigma are estimated from 3 years of historical daily returns. The random seed is fixed for reproducibility.

Output includes percentile fan charts (P5, P10, P25, P50, P75, P90, P95) and annual checkpoint projections.

---

## Robo Advisor

**Module:** `ai_models.robo_advisor.advisor`

### Goal Planning

Future value computation uses monthly compounding:

```
FV = PV * (1 + r/12)^n + PMT * [((1 + r/12)^n - 1) / (r/12)]
```

Required monthly contribution to reach target:

```
PMT = (Target - PV * (1 + r/12)^n) / [((1 + r/12)^n - 1) / (r/12)]
```

Inflation-adjusted real rate:

```
r_real = (1 + r_nominal) / (1 + r_inflation) - 1
```

Scenario analysis outputs conservative (return -2%), base, and optimistic (return +2%) projections.

### Rebalancing Engine

Drift detection per position:

```
drift_i = |w_current_i - w_target_i|
```

A position is flagged for rebalancing when its drift exceeds the configurable threshold (default 5%).

Trade sequencing:

1. Sell positions with losses first (generates cash and realizes tax losses).
2. Sell overweight positions with gains next.
3. Execute buys of underweight positions.

Tax impact estimate:

```
estimated_tax = max(0, unrealized_gain * effective_cap_gains_rate)
```

---

## Market Predictor

**Module:** `ai_models.market_predictor.predictor`

### Price Forecasting

Current implementation uses Geometric Brownian Motion as a simulation framework. The production upgrade path is to replace GBM with a trained LSTM (Long Short-Term Memory) network using 5 years of OHLCV data plus computed technical indicators.

GBM simulation (500 paths, 30-day horizon by default):

```
P(t+1) = P(t) * (1 + r_t),  r_t ~ N(mu_daily, sigma_daily)
```

Output: median path, P10, P90 confidence bands, direction signal.

### Technical Indicators

| Indicator | Window  | Signal                                 |
| --------- | ------- | -------------------------------------- |
| SMA-20    | 20 days | Short-term trend                       |
| SMA-50    | 50 days | Medium-term trend                      |
| RSI-14    | 14 days | Overbought above 70, oversold below 30 |

### Regime Detection

Rolling 21-day statistics are used to classify market regime:

| Regime   | Condition                                                                           |
| -------- | ----------------------------------------------------------------------------------- |
| BULL     | Rolling mean daily return > 0.0005 AND current volatility < 1.2x historical average |
| BEAR     | Rolling mean daily return < -0.0005 OR current volatility > 1.5x historical average |
| SIDEWAYS | Neither condition above is met                                                      |

---

## Sentiment Analyzer

**Module:** `ai_models.sentiment_analyzer.analyzer`  
**Class:** `SentimentAnalyzer`

### Signal Composition

| Signal   | Weight | Source                  | Description                                            |
| -------- | ------ | ----------------------- | ------------------------------------------------------ |
| News     | 35%    | Yahoo Finance headlines | VADER compound score averaged over recent articles     |
| Momentum | 30%    | Price data              | SMA-20 vs SMA-50 crossover, normalized to [-1, +1]     |
| Volume   | 15%    | Volume data             | Volume ratio vs 20-day average, direction-adjusted     |
| RSI      | 20%    | Price data              | RSI-14 overbought/oversold deviation from neutral zone |

Composite score: weighted sum of signal scores, range [-1, +1].

| Score Range    | Label   |
| -------------- | ------- |
| Above +0.15    | BULLISH |
| -0.15 to +0.15 | NEUTRAL |
| Below -0.15    | BEARISH |

Confidence level is determined by how many signals agree on direction.

### VADER Sentiment

VADER (Valence Aware Dictionary and sEntiment Reasoner) is a lexicon and rule-based model specifically calibrated for financial and social media text. The compound score ranges from -1 (most negative) to +1 (most positive). A keyword-based fallback is used when VADER is not installed.

---

## Factor Models

**Module:** `ai_models.factor_models.models`  
**Class:** `FactorModel`

### Fama-French Factor Proxies

| Factor              | Proxy ETFs      | Description                              |
| ------------------- | --------------- | ---------------------------------------- |
| Market (Mkt-RF)     | SPY minus BIL   | Excess market return                     |
| Size (SMB)          | VB minus VV     | Small-cap minus large-cap                |
| Value (HML)         | VTV minus VUG   | Value minus growth                       |
| Profitability (RMW) | QUAL minus USMV | High minus low profitability             |
| Investment (CMA)    | VBR minus VBK   | Conservative minus aggressive investment |
| Momentum            | MTUM minus USMV | Price momentum                           |

### OLS Regression

Portfolio returns are regressed on factor returns:

```
R_p(t) = alpha + beta_1 * F_1(t) + ... + beta_k * F_k(t) + epsilon(t)
```

Outputs: alpha (annualized), factor betas, t-statistics, p-values, R-squared.

### Brinson-Hood-Beebower Attribution

Decomposes active return into three components:

| Effect      | Formula                         | Description                                    |
| ----------- | ------------------------------- | ---------------------------------------------- |
| Allocation  | sum((w_p - w_b) \* r_b)         | Contribution from over/underweighting sectors  |
| Selection   | sum(w_b \* (r_p - r_b))         | Contribution from stock picking within sectors |
| Interaction | sum((w_p - w_b) \* (r_p - r_b)) | Combined effect                                |

---

## Backtester

**Module:** `ai_models.backtester.backtester`  
**Class:** `BacktestEngine`

### Simulation Logic

Daily event loop:

1. Compute portfolio value at open using yesterday's closing prices.
2. Check whether a rebalance is triggered by calendar date or drift threshold.
3. If rebalancing: compute target shares, calculate trade values, deduct transaction costs.
4. Record daily portfolio value.

### Transaction Cost Model

```
cost_per_trade = sum(|delta_shares| * price) * (bps / 10000)
```

Default: 10 basis points (0.10%) per rebalancing event.

### Performance Metrics Computed

| Metric                | Description                                        |
| --------------------- | -------------------------------------------------- |
| Total Return          | (Final - Initial) / Initial                        |
| Annualized Return     | (1 + Total Return)^(252/days) - 1                  |
| Annualized Volatility | Std(daily returns) \* sqrt(252)                    |
| Sharpe Ratio          | (Ann Return - 5%) / Ann Volatility                 |
| Sortino Ratio         | (Ann Return - 5%) / Downside Deviation             |
| Calmar Ratio          | Ann Return / Max Drawdown                          |
| Max Drawdown          | Peak-to-trough percentage decline                  |
| Alpha                 | Ann Return - [Rf + beta * (Benchmark Return - Rf)] |
| Beta                  | Cov(Port, Benchmark) / Var(Benchmark)              |
| Information Ratio     | Alpha / Tracking Error                             |
| Tracking Error        | Std(Port Return - Benchmark Return) \* sqrt(252)   |

---

## Anomaly Detector

**Module:** `ai_models.anomaly_detector.detector`  
**Class:** `PortfolioAnomalyDetector`

### Isolation Forest

The Isolation Forest partitions the feature space by randomly selecting a feature and split value. Anomalous observations are isolated with fewer splits. The anomaly score is the average path length normalized by the expected path length.

Features used for daily return anomaly detection:

| Feature                     | Description                     |
| --------------------------- | ------------------------------- |
| Portfolio daily return      | Raw return for the day          |
| Rolling 21-day volatility   | Realized volatility regime      |
| Deviation from rolling mean | Distance from recent average    |
| Volume ratio                | Recent volume vs 20-day average |

Contamination parameter: 5% (expected fraction of anomalies).

### Z-Score Outlier Detection

A trading day is flagged when:

```
|Z| = |R_t - mu| / sigma > 3.0
```

This threshold corresponds to less than 0.3% expected occurrence under a normal distribution.

### Transaction Anomalies Detected

| Anomaly Type              | Detection Method                                | Severity |
| ------------------------- | ----------------------------------------------- | -------- |
| Large transaction         | Amount > 3 standard deviations of trade history | Medium   |
| Wash-sale risk            | Buy and sell of same ticker within 30 days      | High     |
| Concentration             | Single position above 40% of portfolio          | High     |
| Asset class concentration | Single asset class above 90%                    | Medium   |

### Herfindahl Index

Measures portfolio concentration:

```
HHI = sum(w_i^2)
```

Fully diversified n-asset portfolio: HHI = 1/n.  
Single-stock portfolio: HHI = 1.0.

Effective N (equivalent number of equal-weight positions):

```
Effective N = 1 / HHI
```

---

## Tax Optimizer

**Module:** `ai_models.tax_optimizer.optimizer`  
**Class:** `TaxOptimizer`

### Harvest Schedule Algorithm

Greedy approach:

1. Filter positions with unrealized loss above minimum threshold (default $500).
2. Sort by loss magnitude (largest losses first).
3. For each candidate, compute tax savings using the applicable rate (long-term if holding >= 365 days, short-term otherwise).
4. Schedule sell and immediate reinvestment into wash-sale-compliant substitute.
5. Flag the repurchase prohibition window (30 days after sale).

### After-Tax Return Model

```
After-tax return = Pretax return
                   - (Dividend yield * Ordinary income rate)
                   - (Pretax return * Turnover rate * Cap gains rate)
```

### Tax-Efficient Rebalancing Priority

| Trade Type                | Priority | Rationale                      |
| ------------------------- | -------- | ------------------------------ |
| Sell with unrealized loss | Highest  | Generates a deductible loss    |
| Buy underweight positions | High     | No tax event                   |
| Sell with long-term gain  | Medium   | Taxed at preferential rates    |
| Sell with short-term gain | Lowest   | Taxed at ordinary income rates |
