"""Celery application configuration."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "quantumwealth.settings.development")

app = Celery("quantumwealth")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# ─── Periodic Tasks ───────────────────────────────────────────────────────────
app.conf.beat_schedule = {
    # Refresh market prices every 5 minutes during market hours
    "refresh-prices-every-5min": {
        "task": "apps.market.tasks.refresh_all_portfolio_prices",
        "schedule": 300.0,
    },
    # Check portfolio drift daily at 6 AM UTC
    "check-portfolio-drift-daily": {
        "task": "apps.portfolio.tasks.check_all_portfolio_drift",
        "schedule": crontab(hour=6, minute=0),
    },
    # Send weekly performance digest on Mondays at 8 AM
    "weekly-performance-digest": {
        "task": "apps.accounts.tasks.send_weekly_performance_digest",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
    },
    # Scan for tax-loss harvesting opportunities daily
    "daily-tax-harvest-scan": {
        "task": "apps.tax.tasks.scan_harvest_opportunities",
        "schedule": crontab(hour=7, minute=0),
    },
}
