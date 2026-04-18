# QuantumWealth

AI-Powered Wealth Management and Robo-Advisory Platform

QuantumWealth is a production-grade, fully containerized Django platform combining modern portfolio theory, machine learning, and real-time market data to deliver institutional-grade wealth management to individual investors.

---

## Directory Structure

```
QuantumWealth/
|-- code/
|   |-- backend/        Django REST API, database models, business logic
|   |-- ai_models/      AI and ML modules (portfolio, risk, tax, sentiment, backtesting)
|-- docs/               Full project documentation
|-- infrastructure/     Nginx configuration, PostgreSQL initialization
|-- scripts/            Utility scripts
|-- docker-compose.yml  Full-stack container orchestration
|-- README.md           This file
```

---

## Quick Start (Docker)

```bash
cp code/backend/.env.example code/backend/.env
# Edit .env: set SECRET_KEY and DB_PASSWORD

docker compose up --build -d
docker compose exec backend python manage.py seed_demo_data
```

| Service      | URL                         |
| ------------ | --------------------------- |
| Swagger UI   | http://localhost/api/docs/  |
| ReDoc        | http://localhost/api/redoc/ |
| Django Admin | http://localhost/admin/     |

Demo login: demo@quantumwealth.ai / Demo1234!

---

## Quick Start (Local)

```bash
cd code/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

---

## AI Modules

| Module              | Algorithms                                                                |
| ------------------- | ------------------------------------------------------------------------- |
| Portfolio Optimizer | Mean-Variance, Black-Litterman, Risk Parity, Hierarchical Risk Parity     |
| Risk Engine         | Historical VaR, Parametric VaR, CVaR, Monte Carlo GBM, 5 Stress Scenarios |
| Robo Advisor        | FV/PMT Goal Planning, ERC Rebalancing, Concentration Detection            |
| Market Predictor    | GBM Price Forecasting, Rolling Regime Detection, RSI + SMA Indicators     |
| Tax Optimizer       | Greedy Harvest Scheduling, After-Tax Return Model, Wash-Sale Calendar     |
| Sentiment Analyzer  | VADER News Scoring, Momentum, Volume, RSI Composite Signal                |
| Factor Models       | Fama-French 5-Factor OLS, BHB Attribution, Sector Decomposition           |
| Backtester          | Event-Driven Simulation, Transaction Costs, Benchmark Comparison          |
| Anomaly Detector    | Isolation Forest, Z-Score Outliers, Wash-Sale Clustering                  |

---

## Documentation

| Document                | Description                                                   |
| ----------------------- | ------------------------------------------------------------- |
| docs/overview.md        | Platform goals, architecture, technology stack                |
| docs/api-reference.md   | Complete endpoint reference with request and response schemas |
| docs/ai-models.md       | Mathematical foundations for all AI and ML modules            |
| docs/database-schema.md | Full table definitions with column types and indexes          |
| docs/architecture.md    | System design, request lifecycle, security model, scalability |
| docs/developer-guide.md | Contributing guide, code style, testing patterns              |
| docs/deployment.md      | Local, Docker, and production deployment instructions         |
| docs/testing.md         | Test suite overview and instructions                          |
| docs/changelog.md       | Version history and change log                                |

---

## License

MIT License. See LICENSE file for details.
