# Database Schema

All tables use PostgreSQL 16. UUIDs are used as primary keys. Timestamps are stored with timezone (UTC). Decimal fields use high precision for financial calculations.

---

## Table: accounts_users

Custom user model extending Django's AbstractBaseUser.

| Column                   | Type          | Nullable | Default  | Description                                                                          |
| ------------------------ | ------------- | -------- | -------- | ------------------------------------------------------------------------------------ |
| id                       | uuid          | No       | uuid4()  | Primary key                                                                          |
| email                    | varchar(254)  | No       |          | Unique login identifier                                                              |
| full_name                | varchar(255)  | No       |          | Display name                                                                         |
| phone_number             | varchar(20)   | Yes      |          | Optional contact number                                                              |
| date_of_birth            | date          | Yes      |          | Used for age-based planning                                                          |
| country                  | varchar(2)    | No       | US       | ISO 3166-1 alpha-2 country code                                                      |
| currency                 | varchar(3)    | No       | USD      | ISO 4217 currency code                                                               |
| password                 | varchar(255)  | No       |          | Bcrypt hash                                                                          |
| is_active                | boolean       | No       | true     | Account enabled flag                                                                 |
| is_staff                 | boolean       | No       | false    | Django admin access                                                                  |
| is_verified              | boolean       | No       | false    | Email verified flag                                                                  |
| verification_token       | uuid          | Yes      |          | One-time email verification token                                                    |
| password_reset_token     | uuid          | Yes      |          | Password reset token                                                                 |
| password_reset_expires   | timestamptz   | Yes      |          | Reset token expiry                                                                   |
| risk_profile             | varchar(30)   | No       | moderate | Enum: conservative, moderate_conservative, moderate, moderate_aggressive, aggressive |
| risk_score               | smallint      | No       | 50       | Normalized questionnaire score 0-100                                                 |
| annual_income            | numeric(18,2) | Yes      |          | For financial planning                                                               |
| net_worth                | numeric(18,2) | Yes      |          | For financial planning                                                               |
| investment_horizon_years | smallint      | No       | 10       | Years until funds needed                                                             |
| tax_bracket_pct          | numeric(5,2)  | No       | 22.00    | Marginal tax rate for tax optimization                                               |
| notify_price_alerts      | boolean       | No       | true     | Push price alert notifications                                                       |
| notify_rebalance         | boolean       | No       | true     | Push rebalance notifications                                                         |
| notify_weekly_digest     | boolean       | No       | true     | Email weekly digest                                                                  |
| notify_tax_opportunities | boolean       | No       | true     | Push tax harvest notifications                                                       |
| created_at               | timestamptz   | No       | now()    | Account creation time                                                                |
| updated_at               | timestamptz   | No       | now()    | Last profile update                                                                  |
| last_login               | timestamptz   | Yes      |          | Populated by SimpleJWT on login                                                      |

**Indexes:** email (unique), id (primary key)

---

## Table: accounts_price_alerts

User-configured price alerts for specific tickers.

| Column       | Type          | Nullable | Default | Description                   |
| ------------ | ------------- | -------- | ------- | ----------------------------- |
| id           | uuid          | No       | uuid4() | Primary key                   |
| user_id      | uuid          | No       |         | FK to accounts_users          |
| ticker       | varchar(20)   | No       |         | Security ticker symbol        |
| alert_type   | varchar(10)   | No       |         | above, below, or change_pct   |
| threshold    | numeric(18,4) | No       |         | Price or percentage threshold |
| is_active    | boolean       | No       | true    | Alert enabled flag            |
| triggered_at | timestamptz   | Yes      |         | Set when alert fires          |
| created_at   | timestamptz   | No       | now()   |                               |

---

## Table: accounts_notifications

In-app notification system.

| Column            | Type         | Nullable | Default | Description                                                                |
| ----------------- | ------------ | -------- | ------- | -------------------------------------------------------------------------- |
| id                | uuid         | No       | uuid4() | Primary key                                                                |
| user_id           | uuid         | No       |         | FK to accounts_users                                                       |
| notification_type | varchar(20)  | No       |         | price_alert, rebalance, tax_harvest, goal_milestone, system, weekly_digest |
| title             | varchar(255) | No       |         | Short notification title                                                   |
| message           | text         | No       |         | Full notification body                                                     |
| data              | jsonb        | No       | {}      | Structured metadata (ticker, portfolio_id, etc.)                           |
| is_read           | boolean      | No       | false   | Read status                                                                |
| read_at           | timestamptz  | Yes      |         | Set when marked read                                                       |
| created_at        | timestamptz  | No       | now()   |                                                                            |

---

## Table: portfolio_portfolios

User investment portfolios.

| Column                  | Type          | Nullable | Default | Description                            |
| ----------------------- | ------------- | -------- | ------- | -------------------------------------- |
| id                      | uuid          | No       | uuid4() | Primary key                            |
| user_id                 | uuid          | No       |         | FK to accounts_users                   |
| name                    | varchar(255)  | No       |         | Portfolio display name                 |
| description             | text          | No       |         | Optional notes                         |
| cash_balance            | numeric(18,4) | No       | 0       | Uninvested cash                        |
| total_value             | numeric(18,4) | No       | 0       | Cash plus market value of all holdings |
| is_active               | boolean       | No       | true    | Soft-delete flag                       |
| target_allocation       | jsonb         | No       | {}      | Map of ticker to target weight         |
| benchmark_ticker        | varchar(20)   | No       | SPY     | Benchmark for comparison               |
| annualized_return       | numeric(10,4) | Yes      |         | Cached from last performance run       |
| sharpe_ratio            | numeric(10,4) | Yes      |         | Cached from last performance run       |
| max_drawdown            | numeric(10,4) | Yes      |         | Cached from last performance run       |
| last_performance_update | timestamptz   | Yes      |         | When cache was last refreshed          |
| created_at              | timestamptz   | No       | now()   |                                        |
| updated_at              | timestamptz   | No       | now()   |                                        |

**Indexes:** user_id, is_active

---

## Table: portfolio_holdings

Individual security positions within a portfolio.

| Column             | Type          | Nullable | Default | Description                                                             |
| ------------------ | ------------- | -------- | ------- | ----------------------------------------------------------------------- |
| id                 | uuid          | No       | uuid4() | Primary key                                                             |
| portfolio_id       | uuid          | No       |         | FK to portfolio_portfolios                                              |
| ticker             | varchar(20)   | No       |         | Security ticker symbol                                                  |
| name               | varchar(255)  | No       |         | Security display name                                                   |
| asset_class        | varchar(20)   | No       | equity  | equity, fixed_income, real_estate, commodity, crypto, cash, alternative |
| quantity           | numeric(18,6) | No       |         | Number of shares or units                                               |
| average_cost       | numeric(18,4) | No       |         | Weighted average cost per share                                         |
| current_price      | numeric(18,4) | No       | 0       | Last refreshed market price                                             |
| market_value       | numeric(18,4) | No       | 0       | quantity \* current_price                                               |
| unrealized_pnl     | numeric(18,4) | No       | 0       | market_value - (quantity \* average_cost)                               |
| unrealized_pnl_pct | numeric(10,4) | No       | 0       | unrealized_pnl / cost_basis \* 100                                      |
| weight             | numeric(8,6)  | No       | 0       | market_value / portfolio total_value                                    |
| day_change         | numeric(18,4) | No       | 0       | Dollar change vs prior close                                            |
| day_change_pct     | numeric(8,4)  | No       | 0       | Percentage change vs prior close                                        |
| price_updated_at   | timestamptz   | Yes      |         | Timestamp of last price refresh                                         |
| updated_at         | timestamptz   | No       | now()   |                                                                         |

**Unique constraint:** (portfolio_id, ticker)  
**Indexes:** portfolio_id, ticker

---

## Table: portfolio_transactions

Full transaction ledger with tax metadata.

| Column              | Type          | Nullable | Default | Description                                                                |
| ------------------- | ------------- | -------- | ------- | -------------------------------------------------------------------------- |
| id                  | uuid          | No       | uuid4() | Primary key                                                                |
| portfolio_id        | uuid          | No       |         | FK to portfolio_portfolios                                                 |
| ticker              | varchar(20)   | No       |         | Security ticker, blank for deposits/withdrawals                            |
| transaction_type    | varchar(15)   | No       |         | buy, sell, deposit, withdrawal, dividend, split, transfer_in, transfer_out |
| quantity            | numeric(18,6) | Yes      |         | Shares traded                                                              |
| price               | numeric(18,4) | Yes      |         | Price per share at execution                                               |
| amount              | numeric(18,4) | No       |         | Total dollar amount                                                        |
| fees                | numeric(18,4) | No       | 0       | Commissions and fees                                                       |
| notes               | text          | No       |         | Free text                                                                  |
| executed_at         | timestamptz   | No       | now()   | Execution timestamp                                                        |
| cost_basis          | numeric(18,4) | Yes      |         | Lot cost basis (for sells)                                                 |
| realized_gain       | numeric(18,4) | Yes      |         | Gain or loss realized (for sells)                                          |
| holding_period_days | integer       | Yes      |         | Days held from first buy                                                   |
| is_long_term        | boolean       | Yes      |         | True when holding_period_days >= 365                                       |

**Indexes:** portfolio_id, executed_at, transaction_type

---

## Table: portfolio_financial_goals

User financial objectives tracked over time.

| Column               | Type          | Nullable | Default | Description                                                    |
| -------------------- | ------------- | -------- | ------- | -------------------------------------------------------------- |
| id                   | uuid          | No       | uuid4() | Primary key                                                    |
| user_id              | uuid          | No       |         | FK to accounts_users                                           |
| name                 | varchar(255)  | No       |         | Goal display name                                              |
| goal_type            | varchar(20)   | No       |         | retirement, education, house, emergency_fund, vacation, custom |
| target_amount        | numeric(18,4) | No       |         | Target savings amount                                          |
| current_amount       | numeric(18,4) | No       | 0       | Amount saved so far                                            |
| monthly_contribution | numeric(18,4) | No       | 0       | Planned monthly addition                                       |
| target_date          | date          | No       |         | Goal deadline                                                  |
| expected_return      | numeric(6,4)  | No       | 0.07    | Annual return assumption                                       |
| inflation_rate       | numeric(5,4)  | No       | 0.03    | Annual inflation assumption                                    |
| is_achieved          | boolean       | No       | false   | Completion flag                                                |
| achieved_at          | timestamptz   | Yes      |         | Set when goal is marked complete                               |
| priority             | smallint      | No       | 1       | Sort priority, lower is higher priority                        |
| notes                | text          | No       |         | Free text notes                                                |
| metadata             | jsonb         | No       | {}      | Extensible metadata store                                      |
| created_at           | timestamptz   | No       | now()   |                                                                |
| updated_at           | timestamptz   | No       | now()   |                                                                |

---

## Table: portfolio_snapshots

Daily portfolio value history for charting and performance analytics.

| Column            | Type          | Nullable | Default | Description                  |
| ----------------- | ------------- | -------- | ------- | ---------------------------- |
| id                | uuid          | No       | uuid4() | Primary key                  |
| portfolio_id      | uuid          | No       |         | FK to portfolio_portfolios   |
| date              | date          | No       |         | Snapshot date                |
| total_value       | numeric(18,4) | No       |         | Total portfolio value        |
| cash_balance      | numeric(18,4) | No       |         | Cash portion                 |
| holdings_value    | numeric(18,4) | No       |         | Invested portion             |
| daily_return_pct  | numeric(10,6) | Yes      |         | Day-over-day return          |
| holdings_snapshot | jsonb         | No       | {}      | Full holdings state at close |

**Unique constraint:** (portfolio_id, date)  
**Indexes:** date, portfolio_id

---

## Table: market_quote_cache

Cached market quotes refreshed by Celery price tasks.

| Column         | Type          | Nullable | Description                    |
| -------------- | ------------- | -------- | ------------------------------ |
| ticker         | varchar(20)   | No       | Primary key                    |
| name           | varchar(255)  | Yes      | Security name                  |
| price          | numeric(18,4) | Yes      | Current price                  |
| previous_close | numeric(18,4) | Yes      | Prior trading day close        |
| change         | numeric(18,4) | Yes      | Dollar change from prior close |
| change_pct     | numeric(10,4) | Yes      | Percentage change              |
| volume         | bigint        | Yes      | Most recent volume             |
| market_cap     | bigint        | Yes      | Market capitalization          |
| week_52_high   | numeric(18,4) | Yes      | 52-week high                   |
| week_52_low    | numeric(18,4) | Yes      | 52-week low                    |
| pe_ratio       | numeric(10,4) | Yes      | Trailing P/E ratio             |
| dividend_yield | numeric(8,4)  | Yes      | Annual dividend yield          |
| beta           | numeric(8,4)  | Yes      | Beta vs S&P 500                |
| updated_at     | timestamptz   | No       | Last refresh timestamp         |

---

## Table: market_watchlists

User-defined lists of securities to monitor.

| Column     | Type         | Nullable | Default      | Description                    |
| ---------- | ------------ | -------- | ------------ | ------------------------------ |
| id         | uuid         | No       | uuid4()      | Primary key                    |
| user_id    | uuid         | No       |              | FK to accounts_users           |
| name       | varchar(100) | No       | My Watchlist | Watchlist name                 |
| tickers    | jsonb        | No       | []           | Ordered list of ticker strings |
| created_at | timestamptz  | No       | now()        |                                |
| updated_at | timestamptz  | No       | now()        |                                |

---

## Celery / Beat Tables

Standard tables created by django-celery-beat and django-celery-results:

| Table                               | Description                        |
| ----------------------------------- | ---------------------------------- |
| django_celery_beat_periodictask     | Periodic task schedule definitions |
| django_celery_beat_crontabschedule  | Cron expression schedules          |
| django_celery_beat_intervalschedule | Interval schedules                 |
| django_celery_results_taskresult    | Stored task results                |

---

## JWT Token Tables

Standard tables created by djangorestframework-simplejwt:

| Table                            | Description               |
| -------------------------------- | ------------------------- |
| token_blacklist_outstandingtoken | All issued refresh tokens |
| token_blacklist_blacklistedtoken | Revoked tokens (logout)   |

---

## Relationships Diagram

```
accounts_users
    |-- portfolio_portfolios (one to many)
    |       |-- portfolio_holdings (one to many, unique on portfolio+ticker)
    |       |-- portfolio_transactions (one to many)
    |       |-- portfolio_snapshots (one to many, unique on portfolio+date)
    |-- portfolio_financial_goals (one to many)
    |-- accounts_price_alerts (one to many)
    |-- accounts_notifications (one to many)
    |-- market_watchlists (one to many)
```
