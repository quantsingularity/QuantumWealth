# API Reference

All endpoints are prefixed with `/api/v1/`. All requests except registration and login require the header:

```
Authorization: Bearer <access_token>
```

Responses follow a standard envelope on error:

```json
{
  "error": true,
  "code": 400,
  "detail": "Description of the error."
}
```

---

## Authentication Endpoints

Base path: `/api/v1/auth/`

| Method           | Endpoint                       | Auth Required | Description                                   |
| ---------------- | ------------------------------ | ------------- | --------------------------------------------- |
| POST             | `register/`                    | No            | Create a new user account                     |
| POST             | `login/`                       | No            | Obtain access and refresh tokens              |
| POST             | `logout/`                      | Yes           | Blacklist the refresh token                   |
| POST             | `token/refresh/`               | No            | Rotate refresh token and get new access token |
| GET              | `me/`                          | Yes           | Retrieve authenticated user profile           |
| PATCH            | `me/`                          | Yes           | Update user profile fields                    |
| POST             | `change-password/`             | Yes           | Change account password                       |
| POST             | `password-reset/`              | No            | Send password reset email                     |
| POST             | `password-reset/confirm/`      | No            | Reset password with token                     |
| GET              | `verify-email/<token>/`        | No            | Verify email address                          |
| POST             | `risk-questionnaire/`          | Yes           | Submit risk tolerance questionnaire           |
| GET              | `notifications/`               | Yes           | List all notifications                        |
| POST             | `notifications/mark_all_read/` | Yes           | Mark all notifications as read                |
| GET              | `notifications/unread_count/`  | Yes           | Count unread notifications                    |
| GET/POST         | `price-alerts/`                | Yes           | List or create price alerts                   |
| GET/PATCH/DELETE | `price-alerts/<id>/`           | Yes           | Manage a single price alert                   |

### Register

**POST** `/api/v1/auth/register/`

Request body:

| Field         | Type   | Required | Notes                          |
| ------------- | ------ | -------- | ------------------------------ |
| email         | string | Yes      | Must be unique                 |
| full_name     | string | Yes      | Display name                   |
| password      | string | Yes      | Minimum 8 characters           |
| password2     | string | Yes      | Must match password            |
| phone_number  | string | No       | E.164 format recommended       |
| date_of_birth | string | No       | ISO 8601 date                  |
| country       | string | No       | ISO 3166-1 alpha-2, default US |
| currency      | string | No       | ISO 4217, default USD          |

Response: `201 Created` with user profile object.

### Login

**POST** `/api/v1/auth/login/`

Request body:

| Field    | Type   | Notes                    |
| -------- | ------ | ------------------------ |
| email    | string | Registered email address |
| password | string | Account password         |

Response:

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": { ... }
}
```

### Risk Questionnaire

**POST** `/api/v1/auth/risk-questionnaire/`

Request body:

| Field   | Type  | Notes                   |
| ------- | ----- | ----------------------- |
| answers | array | Array of answer objects |

Each answer object:

| Field       | Type    | Notes                                                   |
| ----------- | ------- | ------------------------------------------------------- |
| question_id | integer | 1 through 10                                            |
| answer      | integer | Score 1 (most conservative) through 5 (most aggressive) |

Response:

| Field                | Type    | Description                                                                            |
| -------------------- | ------- | -------------------------------------------------------------------------------------- |
| risk_score           | integer | Normalized score 0 through 100                                                         |
| risk_profile         | string  | One of: conservative, moderate_conservative, moderate, moderate_aggressive, aggressive |
| description          | string  | Human-readable profile summary                                                         |
| suggested_allocation | object  | Asset class allocation percentages                                                     |
| updated              | boolean | Whether the profile was saved                                                          |

---

## Portfolio Endpoints

Base path: `/api/v1/portfolio/`

| Method           | Endpoint             | Description                                            |
| ---------------- | -------------------- | ------------------------------------------------------ |
| GET              | ``                   | List all active portfolios                             |
| POST             | ``                   | Create a new portfolio                                 |
| GET              | `<id>/`              | Portfolio detail with holdings and recent transactions |
| PATCH            | `<id>/`              | Update portfolio metadata                              |
| DELETE           | `<id>/`              | Soft-delete portfolio                                  |
| GET              | `<id>/holdings/`     | List all holdings                                      |
| POST             | `<id>/holdings/`     | Add or merge a holding                                 |
| GET              | `<id>/transactions/` | List transactions (paginated, filter by type)          |
| POST             | `<id>/transactions/` | Record a transaction                                   |
| POST             | `<id>/optimize/`     | Run AI portfolio optimization                          |
| GET              | `<id>/performance/`  | Full risk and performance report                       |
| GET              | `<id>/history/`      | Daily value snapshots for charting                     |
| POST             | `<id>/snapshot/`     | Manually trigger a snapshot                            |
| GET/POST         | `goals/`             | List or create financial goals                         |
| GET/PATCH/DELETE | `goals/<id>/`        | Manage a goal                                          |
| POST             | `goals/<id>/plan/`   | Generate AI goal attainment plan                       |

### Create Portfolio

**POST** `/api/v1/portfolio/`

| Field             | Type    | Required | Notes                          |
| ----------------- | ------- | -------- | ------------------------------ |
| name              | string  | Yes      | Portfolio display name         |
| description       | string  | No       | Optional notes                 |
| cash_balance      | decimal | No       | Starting cash, default 0       |
| target_allocation | object  | No       | Map of ticker to target weight |
| benchmark_ticker  | string  | No       | Default SPY                    |

### Add or Merge Holding

**POST** `/api/v1/portfolio/<id>/holdings/`

When a holding for the same ticker already exists, a weighted-average cost merge is performed automatically.

| Field        | Type    | Required | Notes                                                                   |
| ------------ | ------- | -------- | ----------------------------------------------------------------------- |
| ticker       | string  | Yes      | Will be uppercased automatically                                        |
| quantity     | decimal | Yes      | Number of shares or units                                               |
| average_cost | decimal | Yes      | Cost per share at purchase                                              |
| name         | string  | No       | Security name                                                           |
| asset_class  | string  | No       | equity, fixed_income, real_estate, commodity, crypto, cash, alternative |

### Record Transaction

**POST** `/api/v1/portfolio/<id>/transactions/`

| Field            | Type    | Required    | Notes                                                                      |
| ---------------- | ------- | ----------- | -------------------------------------------------------------------------- |
| transaction_type | string  | Yes         | buy, sell, deposit, withdrawal, dividend, split, transfer_in, transfer_out |
| amount           | decimal | Yes         | Total dollar amount                                                        |
| ticker           | string  | Conditional | Required for buy and sell                                                  |
| quantity         | decimal | Conditional | Required for buy and sell                                                  |
| price            | decimal | Conditional | Price per share for buy and sell                                           |
| fees             | decimal | No          | Transaction fees, default 0                                                |
| notes            | string  | No          | Free text notes                                                            |

On sell transactions, realized gain/loss and holding period are computed and stored automatically.

### Portfolio Optimization

**POST** `/api/v1/portfolio/<id>/optimize/`

Rate limit: 10 requests per minute.

| Field          | Type   | Default       | Notes                                                  |
| -------------- | ------ | ------------- | ------------------------------------------------------ |
| strategy       | string | mean_variance | mean_variance, black_litterman, risk_parity, hrp       |
| risk_tolerance | float  | 0.5           | 0.0 (conservative) through 1.0 (aggressive)            |
| target_return  | float  | null          | Annual target return, used in mean_variance only       |
| max_weight     | float  | 0.40          | Maximum single position weight                         |
| constraints    | object | {}            | Optional: views (Black-Litterman), max_weight override |

Response fields:

| Field               | Type   | Description                                                |
| ------------------- | ------ | ---------------------------------------------------------- |
| strategy            | string | Strategy used                                              |
| expected_return     | float  | Annualized expected return                                 |
| expected_volatility | float  | Annualized expected volatility                             |
| sharpe_ratio        | float  | Risk-adjusted return                                       |
| allocations         | array  | Per-ticker current weight, target weight, suggested action |
| efficient_frontier  | array  | Return-volatility pairs sweeping the frontier              |
| metadata            | object | Tickers used, tickers dropped, data period                 |

---

## Market Data Endpoints

Base path: `/api/v1/market/`

| Method   | Endpoint                  | Description                             |
| -------- | ------------------------- | --------------------------------------- |
| GET      | `quote/<ticker>/`         | Live single-ticker quote                |
| POST     | `quotes/bulk/`            | Quotes for up to 50 tickers at once     |
| GET      | `history/<ticker>/`       | OHLCV historical data                   |
| GET      | `predict/<ticker>/`       | AI price prediction and regime          |
| GET      | `search/?q=`              | Security search by name or ticker       |
| GET      | `sectors/`                | YTD performance for all 11 GICS sectors |
| GET/POST | `watchlists/`             | List or create watchlists               |
| GET      | `watchlists/<id>/quotes/` | Live quotes for watchlist tickers       |

### Historical Data Query Parameters

| Parameter | Values                                 | Default | Notes        |
| --------- | -------------------------------------- | ------- | ------------ |
| period    | 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max | 1y      | Date range   |
| interval  | 1m, 5m, 15m, 1h, 1d, 1wk, 1mo          | 1d      | Bar interval |

### Price Prediction Query Parameters

| Parameter    | Type    | Default | Notes                            |
| ------------ | ------- | ------- | -------------------------------- |
| horizon_days | integer | 30      | Forecast horizon in trading days |

---

## Risk Engine Endpoints

Base path: `/api/v1/risk/`

Rate limit: 10 requests per minute for all risk endpoints.

| Method | Endpoint                      | Description                                    |
| ------ | ----------------------------- | ---------------------------------------------- |
| GET    | `report/<portfolio_id>/`      | Full risk and performance report               |
| GET    | `var/<portfolio_id>/`         | Value at Risk and Conditional VaR              |
| POST   | `stress-test/<portfolio_id>/` | Historical stress scenario                     |
| GET    | `monte-carlo/<portfolio_id>/` | Monte Carlo projection                         |
| GET    | `correlation/<portfolio_id>/` | Correlation matrix with high-correlation pairs |

### VaR Query Parameters

| Parameter    | Type    | Default    | Valid Range              |
| ------------ | ------- | ---------- | ------------------------ |
| confidence   | float   | 0.95       | 0.90 through 0.99        |
| horizon_days | integer | 1          | 1 through 252            |
| method       | string  | historical | historical or parametric |

### Stress Test Request Body

| Field    | Type   | Default     | Notes                                                                    |
| -------- | ------ | ----------- | ------------------------------------------------------------------------ |
| scenario | string | 2008_crisis | 2008_crisis, covid_crash, dot_com_bust, rate_shock, inflation_spike, all |

### Monte Carlo Query Parameters

| Parameter     | Type    | Default | Notes             |
| ------------- | ------- | ------- | ----------------- |
| simulations   | integer | 10000   | Capped at 50000   |
| horizon_years | integer | 10      | Projection period |

### Full Risk Report Response Fields

| Field                             | Description                                  |
| --------------------------------- | -------------------------------------------- |
| performance.annualized_return     | Geometric annualized return                  |
| performance.annualized_volatility | Annualized standard deviation                |
| performance.sharpe_ratio          | (Return - 5%) / Volatility                   |
| performance.sortino_ratio         | (Return - 5%) / Downside deviation           |
| performance.calmar_ratio          | Annualized return / Max drawdown             |
| performance.omega_ratio           | Gain-to-loss ratio above threshold           |
| performance.max_drawdown          | Peak-to-trough decline                       |
| risk_metrics.var_95_dollar        | 95% VaR in dollars                           |
| risk_metrics.cvar_95_dollar       | 95% CVaR (expected shortfall) in dollars     |
| stress_tests                      | Dict of scenario names to impact percentages |

---

## Advisor Endpoints

Base path: `/api/v1/advisor/`

| Method | Endpoint                          | Description                        |
| ------ | --------------------------------- | ---------------------------------- |
| POST   | `plan/`                           | AI goal attainment plan            |
| POST   | `rebalance/<portfolio_id>/`       | Rebalancing trade list             |
| GET    | `recommendations/<portfolio_id>/` | Actionable AI recommendations      |
| GET    | `drift/<portfolio_id>/`           | Current allocation drift vs target |
| GET    | `suggested-allocation/`           | Allocation by user risk profile    |

### Goal Plan Request Body

| Field                | Type    | Required | Notes                                                          |
| -------------------- | ------- | -------- | -------------------------------------------------------------- |
| goal_type            | string  | Yes      | retirement, education, house, emergency_fund, vacation, custom |
| target_amount        | decimal | Yes      | Goal target in dollars                                         |
| current_savings      | decimal | Yes      | Current saved amount                                           |
| monthly_contribution | decimal | Yes      | Planned monthly addition                                       |
| target_date          | string  | Yes      | ISO 8601 datetime                                              |
| expected_return      | float   | No       | Annual return assumption, default 0.075                        |
| inflation_rate       | float   | No       | Annual inflation, default 0.03                                 |
| inflation_adjusted   | boolean | No       | Adjust target for inflation, default true                      |

### Rebalance Request Body

| Field           | Type   | Default   | Notes                            |
| --------------- | ------ | --------- | -------------------------------- |
| method          | string | threshold | threshold or calendar            |
| drift_threshold | float  | 0.05      | Minimum drift to trigger a trade |
| min_trade_value | float  | 100.0     | Minimum trade size in dollars    |

---

## Tax Endpoints

Base path: `/api/v1/tax/`

| Method | Endpoint                          | Description                          |
| ------ | --------------------------------- | ------------------------------------ |
| POST   | `harvest/<portfolio_id>/`         | Tax-loss harvesting opportunities    |
| GET    | `gain-loss/<portfolio_id>/`       | Realized gain and loss report        |
| GET    | `asset-location/<portfolio_id>/`  | Optimal account type recommendations |
| POST   | `wash-sale-check/<portfolio_id>/` | Check for wash-sale violations       |

### Gain and Loss Report Query Parameters

| Parameter | Type    | Default      | Notes                             |
| --------- | ------- | ------------ | --------------------------------- |
| tax_year  | integer | Current year | Filters sell transactions by year |

### Wash-Sale Check Request Body

| Field     | Type   | Notes                                   |
| --------- | ------ | --------------------------------------- |
| ticker    | string | Ticker to check                         |
| sell_date | string | Proposed sell date in YYYY-MM-DD format |

---

## Pagination

All list endpoints that return multiple records support pagination:

| Parameter | Default | Notes                     |
| --------- | ------- | ------------------------- |
| page      | 1       | Page number               |
| page_size | 50      | Records per page, max 200 |

Paginated response envelope:

```json
{
  "count": 142,
  "next": "http://localhost/api/v1/portfolio/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

---

## Rate Limits

| Throttle Class | Limit          | Applied To                                           |
| -------------- | -------------- | ---------------------------------------------------- |
| Anonymous      | 20 per minute  | All unauthenticated requests                         |
| Authenticated  | 200 per minute | General API calls                                    |
| AI Heavy       | 10 per minute  | Optimize, full risk report, Monte Carlo, backtesting |
| Market         | 60 per minute  | Quote, history, prediction endpoints                 |
