# Deployment Guide

This guide covers local development setup, Docker Compose deployment, and production hardening for QuantumWealth.

---

## Prerequisites

| Tool           | Minimum Version | Purpose                                         |
| -------------- | --------------- | ----------------------------------------------- |
| Python         | 3.12            | Runtime for backend and AI models               |
| Docker         | 24.0            | Container runtime                               |
| Docker Compose | 2.20            | Multi-service orchestration                     |
| PostgreSQL     | 16              | Primary database (via Docker or managed)        |
| Redis          | 7               | Cache and Celery broker (via Docker or managed) |

---

## Option A: Local Development (Without Docker)

### 1. Create a Virtual Environment

```bash
cd code/backend
python -m venv .venv
source .venv/bin/activate      # Linux and macOS
.venv\Scripts\activate         # Windows
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt

# Optional: AI model extras
pip install -r ../../ai_models/requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with the values appropriate for your local setup:

| Variable               | Local Value                        | Notes                      |
| ---------------------- | ---------------------------------- | -------------------------- |
| SECRET_KEY             | Any 50+ character random string    | Required                   |
| DJANGO_SETTINGS_MODULE | quantumwealth.settings.development | Use dev settings locally   |
| DB_HOST                | localhost                          | Local PostgreSQL           |
| DB_NAME                | quantumwealth                      | Create this database first |
| DB_USER                | qwuser                             | Create this role first     |
| DB_PASSWORD            | qwpassword                         | Set a secure password      |
| REDIS_URL              | redis://localhost:6379/0           | Local Redis                |
| DEBUG                  | True                               | Enable for development     |

### 4. Prepare the Database

```bash
# Create database and role (run as postgres superuser)
psql -U postgres -c "CREATE ROLE qwuser LOGIN PASSWORD 'qwpassword';"
psql -U postgres -c "CREATE DATABASE quantumwealth OWNER qwuser;"
psql -U postgres -d quantumwealth -c "CREATE EXTENSION IF NOT EXISTS uuid-ossp;"

# Run Django migrations
python manage.py migrate
```

### 5. Create a Superuser

```bash
python manage.py createsuperuser
```

### 6. Seed Demo Data (Optional)

```bash
python manage.py seed_demo_data
# Demo credentials: demo@quantumwealth.ai / Demo1234!
```

### 7. Start the Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

### 8. Start Background Workers (Separate Terminals)

```bash
# Celery worker
celery -A quantumwealth worker --loglevel=info --concurrency=2

# Celery beat scheduler (periodic tasks)
celery -A quantumwealth beat --loglevel=info
```

### Service URLs

| Service      | URL                              |
| ------------ | -------------------------------- |
| API          | http://localhost:8000/api/v1/    |
| Swagger UI   | http://localhost:8000/api/docs/  |
| ReDoc        | http://localhost:8000/api/redoc/ |
| Django Admin | http://localhost:8000/admin/     |

---

## Option B: Docker Compose (Recommended)

This runs all services (Django, PostgreSQL, Redis, Celery worker, Celery beat, Nginx) in containers.

### 1. Configure Environment

```bash
cp code/backend/.env.example code/backend/.env
```

Minimum required changes:

| Variable               | Required Value                    |
| ---------------------- | --------------------------------- |
| SECRET_KEY             | 50+ random characters             |
| DB_PASSWORD            | Secure password                   |
| DJANGO_SETTINGS_MODULE | quantumwealth.settings.production |

### 2. Build and Start

```bash
docker compose up --build -d
```

This will:

- Build the Django image from `Dockerfile`
- Start PostgreSQL and wait for health check
- Start Redis and wait for health check
- Run `migrate` and `collectstatic` as part of the entrypoint
- Start Gunicorn (4 workers)
- Start Celery worker and Celery beat
- Start Nginx on port 80

### 3. Verify Services

```bash
docker compose ps
```

Expected output:

| Service       | Status       |
| ------------- | ------------ |
| db            | Up (healthy) |
| redis         | Up (healthy) |
| backend       | Up (healthy) |
| celery_worker | Up           |
| celery_beat   | Up           |
| nginx         | Up           |

### 4. Seed Demo Data

```bash
docker compose exec backend python manage.py seed_demo_data
```

### 5. Common Operations

| Task              | Command                                                                       |
| ----------------- | ----------------------------------------------------------------------------- |
| View logs         | `docker compose logs -f`                                                      |
| Restart backend   | `docker compose restart backend`                                              |
| Open Django shell | `docker compose exec backend python manage.py shell`                          |
| Run migrations    | `docker compose exec backend python manage.py migrate`                        |
| Create superuser  | `docker compose exec backend python manage.py createsuperuser`                |
| Export API schema | `docker compose exec backend python manage.py spectacular --file schema.yaml` |

---

## Production Hardening

### Required Environment Changes

| Variable               | Production Value                         |
| ---------------------- | ---------------------------------------- |
| DEBUG                  | False                                    |
| SECRET_KEY             | Cryptographically random, 50+ characters |
| ALLOWED_HOSTS          | Your actual domain name                  |
| DJANGO_SETTINGS_MODULE | quantumwealth.settings.production        |
| CORS_ORIGINS           | Your frontend domain only                |

### SSL/TLS Configuration

The production Nginx config (`infrastructure/nginx/nginx.conf`) should be updated to add a server block for HTTPS. The recommended approach is to use Certbot with Let's Encrypt:

```bash
certbot --nginx -d yourdomain.com
```

After obtaining the certificate, update `nginx.conf` to:

- Listen on port 443 with SSL
- Redirect all HTTP traffic to HTTPS
- Set HSTS header

### Gunicorn Workers

The default worker count is 4. A general rule is to use `2 * CPU_cores + 1` workers. Update the `docker-compose.yml` command:

```
--workers 9
```

For high-throughput AI endpoints (Monte Carlo, optimization), consider using `--worker-class gevent` with `pip install gevent` to handle concurrent long-running requests.

### Database Connection Pooling

For production with high concurrency, configure `CONN_MAX_AGE` and consider adding PgBouncer as a connection pooler between Django and PostgreSQL. This is especially important because portfolio optimization and Monte Carlo operations hold connections open while computing.

### Celery Concurrency

The default Celery worker uses 4 concurrent processes. For AI-heavy workloads, separate queues are recommended:

```bash
# General tasks
celery -A quantumwealth worker -Q default --concurrency=4

# AI computation tasks (separate worker with more memory)
celery -A quantumwealth worker -Q ai_tasks --concurrency=2 --max-tasks-per-child=10
```

### Health Checks

| Endpoint           | Expected Response | Use                 |
| ------------------ | ----------------- | ------------------- |
| `/api/schema/`     | 200 OK            | Backend liveness    |
| `/health/` (Nginx) | 200 OK            | Load balancer probe |

---

## Makefile Reference

Run from the `code/backend/` directory.

| Target        | Command              | Description                     |
| ------------- | -------------------- | ------------------------------- |
| install       | `make install`       | Install Python dependencies     |
| dev           | `make dev`           | Start development server        |
| migrate       | `make migrate`       | Apply all migrations            |
| migrations    | `make migrations`    | Create new migration files      |
| shell         | `make shell`         | Open Django shell               |
| superuser     | `make superuser`     | Create admin user               |
| seed          | `make seed`          | Seed demo data                  |
| test          | `make test`          | Run full test suite             |
| test-coverage | `make test-coverage` | Tests with HTML coverage report |
| lint          | `make lint`          | Flake8 linting                  |
| format        | `make format`        | Black and isort formatting      |
| celery-worker | `make celery-worker` | Start Celery worker (dev)       |
| celery-beat   | `make celery-beat`   | Start Celery beat (dev)         |
| docker-up     | `make docker-up`     | Start all Docker services       |
| docker-down   | `make docker-down`   | Stop all Docker services        |
| docker-logs   | `make docker-logs`   | Tail Docker logs                |
| schema        | `make schema`        | Export OpenAPI schema           |

---

## Environment Variables Reference

Full list of all supported environment variables.

| Variable                    | Default                            | Required          | Description                                     |
| --------------------------- | ---------------------------------- | ----------------- | ----------------------------------------------- |
| SECRET_KEY                  | (none)                             | Yes               | Django secret key, minimum 50 random characters |
| DEBUG                       | False                              | No                | Enable debug mode and verbose logging           |
| ALLOWED_HOSTS               | localhost,127.0.0.1                | Yes in production | Comma-separated allowed hostnames               |
| DJANGO_SETTINGS_MODULE      | quantumwealth.settings.development | No                | Settings module path                            |
| FRONTEND_URL                | http://localhost:3000              | No                | Used in email verification links                |
| DB_NAME                     | quantumwealth                      | No                | PostgreSQL database name                        |
| DB_USER                     | qwuser                             | No                | PostgreSQL role name                            |
| DB_PASSWORD                 | qwpassword                         | Yes in production | PostgreSQL password                             |
| DB_HOST                     | localhost                          | No                | PostgreSQL host                                 |
| DB_PORT                     | 5432                               | No                | PostgreSQL port                                 |
| REDIS_URL                   | redis://localhost:6379/0           | No                | Redis connection URL                            |
| ACCESS_TOKEN_MINUTES        | 60                                 | No                | JWT access token lifetime                       |
| REFRESH_TOKEN_DAYS          | 7                                  | No                | JWT refresh token lifetime                      |
| CORS_ORIGINS                | http://localhost:3000,...          | No                | Comma-separated allowed origins                 |
| ALPHA_VANTAGE_API_KEY       | demo                               | No                | Alpha Vantage API key for extended market data  |
| POLYGON_API_KEY             | (empty)                            | No                | Polygon.io API key                              |
| FINNHUB_API_KEY             | (empty)                            | No                | Finnhub API key                                 |
| OPENAI_API_KEY              | (empty)                            | No                | OpenAI API key for LLM features                 |
| EMAIL_BACKEND               | console                            | No                | Django email backend class                      |
| SMTP_HOST                   | smtp.gmail.com                     | No                | SMTP server hostname                            |
| SMTP_PORT                   | 587                                | No                | SMTP server port                                |
| SMTP_USER                   | (empty)                            | No                | SMTP authentication username                    |
| SMTP_PASSWORD               | (empty)                            | No                | SMTP authentication password                    |
| DEFAULT_FROM_EMAIL          | noreply@quantumwealth.ai           | No                | Sender address for outbound emails              |
| AI_MARKET_DATA_PERIOD       | 2y                                 | No                | Historical data window for AI models            |
| AI_MONTE_CARLO_DEFAULT_SIMS | 10000                              | No                | Default Monte Carlo simulation count            |
| AI_SIMULATION_SEED          | 42                                 | No                | NumPy random seed for reproducibility           |
