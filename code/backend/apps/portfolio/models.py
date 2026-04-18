"""
QuantumWealth — Portfolio Models
Portfolio, Holding, Transaction, FinancialGoal, PortfolioSnapshot.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class AssetClass(models.TextChoices):
    EQUITY = "equity", "Equity"
    FIXED_INCOME = "fixed_income", "Fixed Income"
    REAL_ESTATE = "real_estate", "Real Estate"
    COMMODITY = "commodity", "Commodity"
    CRYPTO = "crypto", "Crypto"
    CASH = "cash", "Cash"
    ALTERNATIVE = "alternative", "Alternative"


class TransactionType(models.TextChoices):
    BUY = "buy", "Buy"
    SELL = "sell", "Sell"
    DIVIDEND = "dividend", "Dividend"
    DEPOSIT = "deposit", "Deposit"
    WITHDRAWAL = "withdrawal", "Withdrawal"
    SPLIT = "split", "Stock Split"
    TRANSFER_IN = "transfer_in", "Transfer In"
    TRANSFER_OUT = "transfer_out", "Transfer Out"


class GoalType(models.TextChoices):
    RETIREMENT = "retirement", "Retirement"
    EDUCATION = "education", "Education"
    HOUSE = "house", "House Purchase"
    EMERGENCY_FUND = "emergency_fund", "Emergency Fund"
    VACATION = "vacation", "Vacation"
    CUSTOM = "custom", "Custom"


class Portfolio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolios"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cash_balance = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0")
    )
    total_value = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0")
    )
    is_active = models.BooleanField(default=True)
    target_allocation = models.JSONField(default=dict, blank=True)
    benchmark_ticker = models.CharField(max_length=20, default="SPY")

    # Performance cache (updated by Celery tasks)
    annualized_return = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    sharpe_ratio = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    max_drawdown = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    last_performance_update = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "portfolio_portfolios"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user.email})"

    @property
    def unrealized_pnl(self):
        return sum(h.unrealized_pnl for h in self.holdings.all())

    @property
    def cost_basis(self):
        return sum(h.quantity * h.average_cost for h in self.holdings.all())


class Holding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="holdings"
    )
    ticker = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    asset_class = models.CharField(
        max_length=20, choices=AssetClass.choices, default=AssetClass.EQUITY
    )
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    average_cost = models.DecimalField(max_digits=18, decimal_places=4)
    current_price = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0")
    )
    market_value = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0")
    )
    unrealized_pnl = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0")
    )
    unrealized_pnl_pct = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal("0")
    )
    weight = models.DecimalField(max_digits=8, decimal_places=6, default=Decimal("0"))
    day_change = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0")
    )
    day_change_pct = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("0")
    )
    price_updated_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "portfolio_holdings"
        unique_together = [("portfolio", "ticker")]
        ordering = ["-market_value"]

    def __str__(self):
        return f"{self.ticker} × {self.quantity} @ {self.portfolio.name}"

    def recalculate(self):
        self.market_value = self.quantity * self.current_price
        cost = self.quantity * self.average_cost
        self.unrealized_pnl = self.market_value - cost
        self.unrealized_pnl_pct = (
            (self.unrealized_pnl / cost * 100) if cost > 0 else Decimal("0")
        )


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="transactions"
    )
    ticker = models.CharField(max_length=20, blank=True)
    transaction_type = models.CharField(max_length=15, choices=TransactionType.choices)
    quantity = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    price = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    fees = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    notes = models.TextField(blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)
    # For tax tracking
    cost_basis = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True
    )
    realized_gain = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True
    )
    holding_period_days = models.PositiveIntegerField(null=True, blank=True)
    is_long_term = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "portfolio_transactions"
        ordering = ["-executed_at"]

    def __str__(self):
        return f"{self.transaction_type.upper()} {self.ticker} @ {self.portfolio.name}"


class FinancialGoal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals"
    )
    name = models.CharField(max_length=255)
    goal_type = models.CharField(max_length=20, choices=GoalType.choices)
    target_amount = models.DecimalField(max_digits=18, decimal_places=4)
    current_amount = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0")
    )
    monthly_contribution = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0")
    )
    target_date = models.DateField()
    expected_return = models.DecimalField(
        max_digits=6, decimal_places=4, default=Decimal("0.07")
    )
    inflation_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.03")
    )
    is_achieved = models.BooleanField(default=False)
    achieved_at = models.DateTimeField(null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=1)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "portfolio_financial_goals"
        ordering = ["priority", "target_date"]

    def __str__(self):
        return f"{self.name} — {self.user.email}"

    @property
    def progress_pct(self):
        if self.target_amount <= 0:
            return 0
        return min(100, float(self.current_amount / self.target_amount * 100))


class PortfolioSnapshot(models.Model):
    """Daily portfolio value snapshots for performance charting."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="snapshots"
    )
    date = models.DateField(db_index=True)
    total_value = models.DecimalField(max_digits=18, decimal_places=4)
    cash_balance = models.DecimalField(max_digits=18, decimal_places=4)
    holdings_value = models.DecimalField(max_digits=18, decimal_places=4)
    daily_return_pct = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True
    )
    holdings_snapshot = models.JSONField(default=dict)

    class Meta:
        db_table = "portfolio_snapshots"
        unique_together = [("portfolio", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.portfolio.name} @ {self.date}: ${self.total_value}"
