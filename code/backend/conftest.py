"""
Root conftest.py — MUST live at code/backend/conftest.py (same dir as pytest.ini).

Calls django.setup() at import time so Django is fully initialized before
pytest collects any test module.  This approach works whether or not
pytest-django is installed.
"""

import os

import django

# Set the settings module before anything else touches Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "quantumwealth.settings.test")

# Initialize Django — this must happen before any import of:
#   - django.contrib.*
#   - rest_framework.*
#   - apps.*
django.setup()

from decimal import Decimal

# ---------------------------------------------------------------------------
# Only import Django / DRF stuff AFTER django.setup() has run
# ---------------------------------------------------------------------------
import pytest

# ---------------------------------------------------------------------------
# Shared fixtures (available to every test file without explicit import)
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    """A saved, active, verified User with moderate risk profile."""
    from tests.conftest import make_user

    return make_user("fixture@qw.ai", "Test1234!")


@pytest.fixture
def user_client(user):
    """An authenticated APIClient for *user*."""
    from tests.conftest import auth_client

    return auth_client(user)


@pytest.fixture
def portfolio(db, user):
    """A basic portfolio with $10,000 cash owned by *user*."""
    from tests.conftest import make_portfolio

    return make_portfolio(user, "Fixture Portfolio", cash=Decimal("10000.00"))


@pytest.fixture
def portfolio_with_holdings(db, portfolio):
    """Portfolio pre-loaded with AAPL (equity) and BND (fixed income)."""
    from tests.conftest import add_holding

    add_holding(
        portfolio, "AAPL", Decimal("10"), Decimal("150.00"), asset_class="equity"
    )
    add_holding(
        portfolio, "BND", Decimal("20"), Decimal("75.00"), asset_class="fixed_income"
    )
    portfolio.refresh_from_db()
    return portfolio
