# Changelog

All notable changes are documented in this file. The format follows Keep a Changelog conventions.

---

## Version 2.0.0 (2026-04-18) -- Django Conversion and Major Expansion

### Architecture

| Change                           | Detail                                                                                               |
| -------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Framework migration              | Converted from FastAPI + separate AI microservice to Django REST Framework with native AI module     |
| Eliminated microservice boundary | AI models are now imported Python modules; no HTTP calls between backend and AI layer                |
| Settings hierarchy               | base / development / production settings with environment variable configuration via python-decouple |
| Celery integration               | Full Celery 5 setup with django-celery-beat for database-backed schedules                            |
| Admin panel                      | Django admin fully wired for all models with inline views                                            |
| API documentation                | Switched from FastAPI auto-docs to drf-spectacular with OpenAPI 3.1, Swagger UI, and ReDoc           |

### New Features

| Feature                       | Description                                                                                              |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| Email verification            | Token-based email verification on registration                                                           |
| Full password reset           | Request email, confirm with token, two-hour expiry                                                       |
| JWT token blacklisting        | Refresh tokens are blacklisted on logout via SimpleJWT blacklist app                                     |
| Extended user model           | Added phone, date of birth, country, currency, tax bracket, investment horizon, notification preferences |
| Price alerts                  | CRUD for user price alerts with Celery-driven checking every 5 minutes                                   |
| In-app notifications          | Full notification system with read/unread state, mark-all-read, unread count                             |
| Watchlists                    | Portfolio watchlists with live quote fetching                                                            |
| Bulk quotes endpoint          | Single POST to fetch quotes for up to 50 tickers                                                         |
| Sector performance            | YTD returns for all 11 GICS sector ETFs                                                                  |
| Portfolio snapshots           | Daily value snapshots for chart rendering                                                                |
| Correlation matrix            | Endpoint returning pairwise correlation with high-correlation pair detection                             |
| All stress scenarios          | Single endpoint call with `scenario=all` returns all five scenarios                                      |
| Inflation spike scenario      | Added 1970s-style inflation shock scenario to stress test suite                                          |
| Omega ratio                   | Added to full risk report                                                                                |
| Wash-sale check endpoint      | POST endpoint to check proposed sell date for wash-sale violations                                       |
| Asset-class-aware harvest     | Tax savings estimates use long-term vs short-term rate based on actual holding period                    |
| Advisor recommendations       | Automatic flagging of concentration risk, missing asset classes, cash drag, rebalancing need             |
| Drift analysis endpoint       | Returns per-position drift from target with needs_rebalancing flag                                       |
| Suggested allocation endpoint | Returns risk-profile-appropriate allocation with expected return and volatility                          |
| Scenario analysis in goals    | Goal plans include conservative, base, and optimistic projections                                        |

### New AI Models

| Module                   | Algorithms                                                                                                                        |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| Hierarchical Risk Parity | Lopez de Prado 2016 clustering and recursive bisection                                                                            |
| Factor Models            | Fama-French 5-factor OLS regression, Brinson-Hood-Beebower attribution, sector correlation decomposition                          |
| Sentiment Analyzer       | VADER news scoring, SMA crossover momentum, volume-direction signal, RSI overbought/oversold                                      |
| Backtester               | Event-driven simulation with transaction costs, drift-triggered and calendar rebalancing, benchmark comparison                    |
| Anomaly Detector         | Isolation Forest for return anomalies, Z-score outlier flagging, transaction wash-sale clustering, Herfindahl concentration index |
| Tax Optimizer            | Greedy harvest schedule with rate-aware savings, tax-efficient rebalancing priority, after-tax return model                       |

### Performance Improvements

| Improvement                 | Detail                                                                           |
| --------------------------- | -------------------------------------------------------------------------------- |
| Weighted-average cost merge | Holdings upsert computes correct average cost rather than overwriting            |
| Realized gain tracking      | Sell transactions record cost basis, gain/loss, holding period at execution time |
| Bulk price refresh          | Single yfinance download for all held tickers rather than one call per ticker    |
| Redis key prefixing         | All cache keys prefixed with `qw:` to prevent collisions                         |

### Bug Fixes vs Original

| Bug                                       | Fix                                                                                           |
| ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| Holding period always 365                 | Now computed from actual first BUY transaction timestamp                                      |
| Tax savings used hardcoded 20% rate       | Now uses user tax_bracket_pct for short-term and min(rate, 20%) for long-term                 |
| Missing password confirmation on register | Added password2 field with validation                                                         |
| No logout mechanism                       | Implemented refresh token blacklisting                                                        |
| Advisor recommendations were empty stubs  | Fully implemented with concentration, diversification, cash drag, rebalancing, and tax checks |

---

## Version 1.0.0 (2026-04-14) -- Initial FastAPI Release

### Features

| Area           | Capabilities                                                                     |
| -------------- | -------------------------------------------------------------------------------- |
| Authentication | JWT login and registration                                                       |
| Portfolio      | CRUD, holdings, transactions, optimization                                       |
| Market         | Quote, history, prediction, search                                               |
| Risk           | VaR, CVaR, Monte Carlo, stress testing                                           |
| Advisor        | Goal planning, rebalancing, risk questionnaire                                   |
| Tax            | Harvest opportunities, gain/loss report, asset location                          |
| AI Models      | Mean-Variance, Black-Litterman, Risk Parity, GBM predictor, HMM regime detection |
| Infrastructure | Docker Compose, PostgreSQL, Redis, Celery, Nginx                                 |

### Known Limitations in v1.0.0

| Limitation                        | Status in v2.0.0         |
| --------------------------------- | ------------------------ |
| No email verification             | Resolved                 |
| No password reset                 | Resolved                 |
| No in-app notifications           | Resolved                 |
| Holding period hardcoded          | Resolved                 |
| Tax rate hardcoded at 20%         | Resolved                 |
| No wash-sale date check           | Resolved                 |
| Advisor recommendations stubbed   | Resolved                 |
| Separate AI microservice required | Resolved (native module) |
| No price alerts                   | Resolved                 |
| No watchlists                     | Resolved                 |
| No correlation matrix endpoint    | Resolved                 |
| No portfolio value history        | Resolved                 |
