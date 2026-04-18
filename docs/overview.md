# QuantumWealth Platform Overview

## What Is QuantumWealth

QuantumWealth is a production-grade, AI-powered wealth management and robo-advisory platform designed to deliver institutional-grade portfolio analytics to individual investors. It combines modern portfolio theory, machine learning, and real-time market data in a fully containerized Django application.

## Platform Goals

- Provide scientifically grounded portfolio construction using mean-variance optimization, Black-Litterman, Risk Parity, and Hierarchical Risk Parity.
- Deliver comprehensive risk analytics including Value at Risk, Conditional VaR, Monte Carlo simulation, and historical stress testing.
- Automate tax-loss harvesting with wash-sale compliance and after-tax return optimization.
- Generate actionable rebalancing recommendations with tax-aware trade sequencing.
- Surface multi-signal market sentiment (news, momentum, volume, RSI).
- Support historical strategy backtesting with transaction cost modeling.
- Detect anomalous portfolio behavior using Isolation Forest and statistical methods.

---

## High-Level Architecture

```
QuantumWealth/
|-- code/
|   |-- backend/          Django REST API, authentication, business logic, database
|   |-- ai_models/        AI and ML modules (importable Python package)
|       |-- portfolio_optimizer/    Four optimization strategies
|       |-- risk_engine/            Risk metrics and stress testing
|       |-- robo_advisor/           Goal planning and rebalancing
|       |-- market_predictor/       Price forecasting and regime detection
|       |-- tax_optimizer/          Tax-loss scheduling and after-tax modeling
|       |-- sentiment_analyzer/     Multi-signal sentiment scoring
|       |-- factor_models/          Fama-French exposure and attribution
|       |-- backtester/             Historical strategy simulation
|       |-- anomaly_detector/       Isolation Forest anomaly detection
|-- docs/                 Full project documentation
|-- infrastructure/       Nginx, PostgreSQL initialization scripts
|-- scripts/              Utility and deployment scripts
```

---

## Technology Stack

| Layer          | Technology                         | Purpose                              |
| -------------- | ---------------------------------- | ------------------------------------ |
| Web Framework  | Django 5 and Django REST Framework | REST API, ORM, admin panel           |
| Authentication | SimpleJWT with token blacklisting  | Stateless auth with refresh rotation |
| Database       | PostgreSQL 16 with psycopg3        | Primary data store                   |
| Cache          | Redis 7 via django-redis           | Quote caching and session data       |
| Task Queue     | Celery 5 with django-celery-beat   | Background and periodic tasks        |
| Portfolio Math | NumPy, SciPy, cvxpy                | Optimization and statistics          |
| Market Data    | yfinance                           | Historical and live price data       |
| ML Models      | scikit-learn                       | Isolation Forest anomaly detection   |
| API Docs       | drf-spectacular                    | OpenAPI 3.1 schema, Swagger, ReDoc   |
| Reverse Proxy  | Nginx                              | Rate limiting, static files, SSL     |
| Containers     | Docker and Docker Compose          | Full-stack orchestration             |

---

## Key Design Decisions

### Monolithic AI Integration

The AI models are native Python modules imported directly by Django, rather than a separate microservice. This removes network latency, simplifies deployment, reduces operational overhead, and makes debugging straightforward with a single process tree.

### Synchronous Computation with Task Offloading

Heavy computations (Monte Carlo, backtests) are designed to run synchronously for small portfolios and can be offloaded to Celery workers for production workloads by wrapping the service call in a Celery task.

### Tax-Aware Transaction Recording

Every sell transaction records cost basis, realized gain/loss, holding period in days, and long/short-term classification at execution time, enabling accurate reporting without reconstructing history later.

### Redis Caching for Market Data

Live quotes are cached for 60 seconds, historical OHLCV data for 1 hour, and search results for 1 hour. This prevents rate-limit issues from yfinance and keeps the UI responsive.

---

## User Roles and Access Control

| Role               | Description             | Access Level                     |
| ------------------ | ----------------------- | -------------------------------- |
| Anonymous          | Unauthenticated visitor | Register and login only          |
| Authenticated User | Verified account holder | Full platform access to own data |
| Staff              | Internal team member    | Django admin read access         |
| Superuser          | Platform administrator  | Full Django admin access         |

---

## Compliance Considerations

- Wash-sale detection flags buy and sell of the same security within 30 days on either side of a loss sale.
- Tax-loss harvesting recommendations include IRS-compliant substitute securities.
- All financial computations are informational only. The platform does not constitute registered investment advice.
- User passwords are hashed with bcrypt. JWT tokens use HS256 signing with configurable expiry.
- Refresh tokens are blacklisted on logout to prevent reuse.
