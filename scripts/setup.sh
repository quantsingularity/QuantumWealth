#!/usr/bin/env bash
# setup.sh -- One-command local development setup
set -euo pipefail

echo "=== QuantumWealth Local Setup ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_MAJOR=3
REQUIRED_MINOR=12
echo "Python version: $PYTHON_VERSION"

cd "$(dirname "$0")/../code/backend"

# Create virtual environment
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "Installing AI model dependencies..."
pip install -r ../ai_models/requirements.txt --quiet 2>/dev/null || true

# Copy env file
if [ ! -f ".env" ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
  echo "IMPORTANT: Edit code/backend/.env and set SECRET_KEY before running the server."
fi

echo "Applying migrations..."
DJANGO_SETTINGS_MODULE=quantumwealth.settings.development python manage.py migrate --noinput

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
