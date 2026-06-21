# Run from the code/backend/ directory, as documented in docs/deployment.md.
# All commands assume a virtual environment has already been created and
# activated (see docs/deployment.md, Option A, steps 1-3).

.PHONY: install dev migrate migrations shell superuser seed test test-coverage \
        lint format celery-worker celery-beat docker-up docker-down docker-logs schema

install:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r ../ai_models/requirements.txt
	pip install -r requirements-dev.txt

dev:
	python manage.py runserver 0.0.0.0:8000

migrate:
	python manage.py migrate

migrations:
	python manage.py makemigrations

shell:
	python manage.py shell

superuser:
	python manage.py createsuperuser

seed:
	python manage.py seed_demo_data

test:
	pytest

test-coverage:
	pytest --cov=apps --cov=quantumwealth --cov-report=html --cov-report=term-missing

lint:
	flake8 apps quantumwealth --exclude=migrations

format:
	isort apps quantumwealth
	black apps quantumwealth

celery-worker:
	celery -A quantumwealth worker --loglevel=info --concurrency=2

celery-beat:
	celery -A quantumwealth beat --loglevel=info

docker-up:
	cd ../.. && docker compose up --build -d

docker-down:
	cd ../.. && docker compose down

docker-logs:
	cd ../.. && docker compose logs -f

schema:
	python manage.py spectacular --file schema.yaml
