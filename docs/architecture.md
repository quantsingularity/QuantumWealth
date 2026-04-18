# Architecture Guide

---

## System Architecture

```
                        Internet
                           |
                      [ Nginx ]
                      Port 80/443
                    /           \
            /static/          /api/v1/
               |                  |
        Static Files         [ Gunicorn ]
        (WhiteNoise)         Django + DRF
                                  |
                    +-------------+-----------+
                    |             |           |
               [ PostgreSQL ] [ Redis ]  [ Celery ]
               Primary DB    Cache/Queue  Workers
                                  |
                             [ ai_models ]
                             Native Python
                             (no microservice)
```

---

## Application Layers

### Layer 1: HTTP / Transport

Nginx handles all incoming traffic on port 80 (and 443 in production). It enforces rate limits at the connection level before requests reach Django, serves static files directly without touching Python, and proxies all `/api/` and `/admin/` requests to Gunicorn.

| Nginx Role          | Detail                                            |
| ------------------- | ------------------------------------------------- |
| Rate limiting       | Auth: 10 req/min, API: 30 req/min                 |
| Static serving      | `/static/` served directly from disk              |
| SSL termination     | Terminates TLS, forwards plain HTTP to Gunicorn   |
| Upstream keep-alive | 32 persistent connections to Gunicorn             |
| Request buffering   | Buffers slow clients to prevent blocking Gunicorn |

### Layer 2: WSGI Application Server

Gunicorn runs 4 synchronous worker processes (configurable). Each worker handles one request at a time. For production workloads with concurrent AI requests, switching to async workers (gevent) is recommended.

| Gunicorn Setting | Value     | Rationale                                         |
| ---------------- | --------- | ------------------------------------------------- |
| workers          | 4         | 2 \* CPU + 1 rule                                 |
| worker_class     | sync      | Simple, stable for most workloads                 |
| timeout          | 120s      | AI endpoints can be slow                          |
| max_requests     | (not set) | Workers restart automatically on unhandled errors |

### Layer 3: Django Application

The Django application is organized into six focused apps:

| App       | Responsibility                                                                |
| --------- | ----------------------------------------------------------------------------- |
| accounts  | Authentication, user profile, risk questionnaire, notifications, price alerts |
| portfolio | Portfolio CRUD, holdings, transactions, goals, daily snapshots                |
| market    | Quote caching, OHLCV history, price prediction, watchlists                    |
| risk      | VaR, CVaR, Monte Carlo, stress testing, correlation                           |
| advisor   | Goal planning, rebalancing, recommendations, allocation drift                 |
| tax       | Tax-loss harvesting, gain/loss reporting, asset location, wash-sale check     |

Each app follows the standard Django pattern: `models.py`, `serializers.py`, `views.py`, `urls.py`, `services.py`, `tasks.py`, `admin.py`.

### Layer 4: AI Engine (Native Module)

The `ai_models` package lives in `code/ai_models/` and is imported directly by Django service classes. There is no network boundary, no serialization overhead, and no separate process to manage.

| Module              | Entry Point                                        | Key Algorithms                                   |
| ------------------- | -------------------------------------------------- | ------------------------------------------------ |
| portfolio_optimizer | PortfolioOptimizer.optimize()                      | Mean-Variance, Black-Litterman, Risk Parity, HRP |
| risk_engine         | RiskEngine.full_report()                           | VaR, CVaR, Monte Carlo GBM, stress scenarios     |
| robo_advisor        | plan_goal(), compute_rebalance()                   | FV/PMT solver, recursive bisection               |
| market_predictor    | LSTMPredictor.predict()                            | GBM simulation, RSI, SMA crossover               |
| tax_optimizer       | TaxOptimizer.optimize_harvest_schedule()           | Greedy harvest scheduling                        |
| sentiment_analyzer  | SentimentAnalyzer.analyze_ticker()                 | VADER, momentum, volume, RSI composite           |
| factor_models       | FactorModel.compute_factor_exposures()             | OLS regression, BHB attribution                  |
| backtester          | BacktestEngine.run()                               | Event-driven simulation with costs               |
| anomaly_detector    | PortfolioAnomalyDetector.detect_return_anomalies() | Isolation Forest, z-score                        |

### Layer 5: Data Layer

#### PostgreSQL

All persistent state lives in PostgreSQL. The ORM is Django's standard ORM (synchronous). Key design decisions:

- UUID primary keys prevent enumeration attacks and simplify distributed inserts.
- JSONB columns store flexible data (target_allocation, holdings_snapshot, notification data) without schema migrations for every new field.
- Decimal fields use `numeric(18,4)` for financial precision and `numeric(18,6)` for quantities.
- Soft deletes on portfolios preserve transaction history.
- `CONN_MAX_AGE=60` keeps database connections open across requests within a worker.

#### Redis

Redis serves two roles: a Django cache backend and a Celery message broker.

| Redis Key Pattern                                | TTL   | Content                 |
| ------------------------------------------------ | ----- | ----------------------- |
| `qw:market:quote:<ticker>`                       | 60s   | Live quote dict         |
| `qw:market:history:<ticker>:<period>:<interval>` | 3600s | OHLCV list              |
| `qw:market:predict:<ticker>:<days>`              | 1800s | Prediction dict         |
| `qw:market:search:<query>`                       | 3600s | Search results list     |
| `qw:market:sectors`                              | 3600s | Sector performance dict |

---

## Request Lifecycle

### Typical API Request

```
Client
  --> Nginx (rate limit check, static bypass)
  --> Gunicorn worker
  --> Django URL router
  --> DRF view (authentication, throttle, permission checks)
  --> Service layer (business logic)
  --> Django ORM (database query)
  --> (optional) Redis cache lookup
  --> (optional) ai_models call
  --> JSON serializer
  --> Response
```

### Background Task (Celery)

```
Celery Beat (scheduler)
  --> Enqueues task message into Redis
  --> Celery worker picks up message
  --> Task function runs (fetches prices, checks drift, sends email)
  --> Results stored in django_celery_results_taskresult table
```

---

## Celery Periodic Tasks

| Task Name                      | Schedule                 | Description                                                                                                    |
| ------------------------------ | ------------------------ | -------------------------------------------------------------------------------------------------------------- |
| refresh_all_portfolio_prices   | Every 5 minutes          | Fetches live prices for all held tickers, updates holdings, recalculates portfolio values, checks price alerts |
| check_all_portfolio_drift      | Daily at 6 AM UTC        | Computes allocation drift for portfolios with targets; notifies users when threshold is breached               |
| scan_harvest_opportunities     | Daily at 7 AM UTC        | Scans all holdings for unrealized losses above $100; notifies opted-in users                                   |
| send_weekly_performance_digest | Every Monday at 8 AM UTC | Sends weekly portfolio summary email to opted-in users                                                         |

---

## Security Architecture

### Authentication Flow

```
1. POST /api/v1/auth/login/  -->  SimpleJWT validates credentials
2. Returns access token (60 min) + refresh token (7 days)
3. Client sends: Authorization: Bearer <access_token>
4. SimpleJWT middleware validates signature and expiry
5. get_current_user() loads User from database
6. On logout: POST /api/v1/auth/logout/ blacklists the refresh token
```

### Token Storage

Access tokens are short-lived (60 minutes) and stored in client memory. Refresh tokens are longer-lived (7 days) and should be stored in httpOnly cookies in production to prevent XSS access.

### Defense in Depth

| Layer             | Control                                                   |
| ----------------- | --------------------------------------------------------- |
| Nginx             | Rate limiting per IP, request size limits                 |
| Django Middleware | CSRF protection, clickjacking headers, XSS protection     |
| DRF Throttling    | Per-endpoint request rate limits                          |
| JWT               | Signed tokens with expiry; refresh token blacklisting     |
| Password Hashing  | bcrypt via Passlib                                        |
| Database          | UUID primary keys, parameterized queries via ORM          |
| Production Django | HSTS, SSL redirect, secure cookies, X-Frame-Options: DENY |

---

## Scalability Considerations

### Horizontal Scaling

The backend is stateless (session data in Redis, no local file state). Multiple Gunicorn instances can run behind a load balancer sharing the same PostgreSQL and Redis.

### Celery Scaling

AI computation tasks can be separated onto dedicated workers with more memory. Queue routing:

```python
# In celery task decorator
@shared_task(queue="ai_tasks")
def run_monte_carlo_async(portfolio_id): ...
```

Workers can be scaled independently:

```bash
celery -A quantumwealth worker -Q default --concurrency=8
celery -A quantumwealth worker -Q ai_tasks --concurrency=2
```

### Caching Strategy

| Data Type               | Cache TTL  | Rationale                                       |
| ----------------------- | ---------- | ----------------------------------------------- |
| Live quotes             | 60 seconds | Balance freshness with API rate limits          |
| Historical OHLCV        | 1 hour     | Intraday data rarely changes                    |
| AI predictions          | 30 minutes | Computationally expensive, acceptable staleness |
| Sector performance      | 1 hour     | Updated once daily by exchanges                 |
| Security search results | 1 hour     | Stable reference data                           |

### Database Optimization

For portfolios with many transactions (10,000+), add a partial index on transaction execution date:

```sql
CREATE INDEX idx_transactions_portfolio_year
ON portfolio_transactions (portfolio_id, executed_at)
WHERE transaction_type = 'sell';
```

For the gain/loss report query which filters by year, this reduces scan time significantly.

---

## Monitoring

### Recommended Stack

| Tool       | Purpose                         | Integration                      |
| ---------- | ------------------------------- | -------------------------------- |
| Sentry     | Error tracking and stack traces | `pip install sentry-sdk`         |
| Prometheus | Metrics scraping                | `pip install django-prometheus`  |
| Grafana    | Metrics dashboards              | Connect to Prometheus            |
| Flower     | Celery task monitoring          | `celery -A quantumwealth flower` |
| pgBadger   | PostgreSQL slow query analysis  | Parse PostgreSQL logs            |

### Key Metrics to Track

| Metric                      | Alert Threshold             | Description                            |
| --------------------------- | --------------------------- | -------------------------------------- |
| API p95 latency             | Over 2 seconds              | Slow endpoint detection                |
| AI endpoint latency         | Over 10 seconds             | Optimization or Monte Carlo regression |
| Celery task failure rate    | Over 5%                     | Background task health                 |
| Redis memory usage          | Over 80%                    | Cache eviction risk                    |
| PostgreSQL connection count | Over 80% of max_connections | Connection pool saturation             |
| Error rate (5xx)            | Over 1%                     | Application health                     |
