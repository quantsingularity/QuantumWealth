"""Market app — models for cached quotes and watchlists."""

import uuid

from django.conf import settings
from django.db import models


class MarketQuoteCache(models.Model):
    """Cached market quote — refreshed by Celery task."""

    ticker = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    previous_close = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    change = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    change_pct = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    volume = models.BigIntegerField(null=True)
    market_cap = models.BigIntegerField(null=True)
    week_52_high = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    week_52_low = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    pe_ratio = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    dividend_yield = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    beta = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "market_quote_cache"

    def __str__(self):
        return f"{self.ticker}: ${self.price}"


class Watchlist(models.Model):
    """User watchlists for tracking securities."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlists"
    )
    name = models.CharField(max_length=100, default="My Watchlist")
    tickers = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "market_watchlists"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user.email})"
