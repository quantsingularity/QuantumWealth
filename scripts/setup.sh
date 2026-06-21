#!/usr/bin/env bash
# setup.sh -- One-command local development setup
set -euo pipefail

echo "=== QuantumWealth Local Setup ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_MAJOR=3
REQUIRED_MINOR=12
echo "Python version: $PYTHON_VERSION"

# FIX: REQUIRED_MAJOR/REQUIRED_MINOR were declared above but never
# actually compared against anything, so this check did nothing - the
# script proceeded silently on any Python version, including ones too old
# for this project, only to fail later with a more confusing error.
PY_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt "$REQUIRED_MAJOR" ] || { [ "$PY_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$PY_MINOR" -lt "$REQUIRED_MINOR" ]; }; then
  echo "ERROR: Python $REQUIRED_MAJOR.$REQUIRED_MINOR or newer is required (found $PYTHON_VERSION)."
  exit 1
fi

cd "$(dirname "$0")/../code/backend"

# Create virtual environment
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

echo "Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "Installing AI model dependencies..."
if ! pip install -r ../ai_models/requirements.txt --quiet; then
  echo "WARNING: failed to install AI model dependencies. AI-powered"
  echo "features (portfolio optimization, risk analysis, the robo-advisor,"
  echo "and market prediction) will not work until this is resolved."
  echo "Run 'pip install -r ../ai_models/requirements.txt' manually to see"
  echo "the actual error."
fi

# Copy env file
if [ ! -f ".env" ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
  echo "IMPORTANT: Edit code/backend/.env and set SECRET_KEY before running the server."
fi

echo "Applying migrations..."
if ! DJANGO_SETTINGS_MODULE=quantumwealth.settings.development python manage.py migrate --noinput; then
  echo ""
  echo "ERROR: migrations failed. This usually means the local PostgreSQL"
  echo "database and role haven't been created yet. Run (as the postgres"
  echo "superuser), matching the values in your .env file:"
  echo "  psql -U postgres -c \"CREATE ROLE qwuser LOGIN PASSWORD 'qwpassword';\""
  echo "  psql -U postgres -c \"CREATE DATABASE quantumwealth OWNER qwuser;\""
  echo "Then re-run this script, or just 'python manage.py migrate' again."
  exit 1
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  source code/backend/.venv/bin/activate"
echo "  cd code/backend"
echo "  python manage.py seed_demo_data     # optional demo data"
echo "  python manage.py runserver          # start development server"
echo ""
echo "Demo login: demo@quantumwealth.ai / Demo1234!"
