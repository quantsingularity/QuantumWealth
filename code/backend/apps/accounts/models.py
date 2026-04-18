"""
QuantumWealth — Accounts Models
Custom User model with risk profiling and financial profile.
"""

import uuid
from decimal import Decimal

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class RiskProfile(models.TextChoices):
    CONSERVATIVE = "conservative", "Conservative"
    MODERATE_CONSERVATIVE = "moderate_conservative", "Moderate Conservative"
    MODERATE = "moderate", "Moderate"
    MODERATE_AGGRESSIVE = "moderate_aggressive", "Moderate Aggressive"
    AGGRESSIVE = "aggressive", "Aggressive"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=2, default="US")  # ISO 3166-1 alpha-2
    currency = models.CharField(max_length=3, default="USD")

    # Auth & verification
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(null=True, blank=True)
    password_reset_token = models.UUIDField(null=True, blank=True)
    password_reset_expires = models.DateTimeField(null=True, blank=True)

    # Risk profiling
    risk_profile = models.CharField(
        max_length=30, choices=RiskProfile.choices, default=RiskProfile.MODERATE
    )
    risk_score = models.PositiveSmallIntegerField(default=50, help_text="0-100")

    # Financial profile
    annual_income = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    net_worth = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    investment_horizon_years = models.PositiveSmallIntegerField(default=10)
    tax_bracket_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("22.00"),
        help_text="Marginal tax rate in percent",
    )

    # Notification preferences
    notify_price_alerts = models.BooleanField(default=True)
    notify_rebalance = models.BooleanField(default=True)
    notify_weekly_digest = models.BooleanField(default=True)
    notify_tax_opportunities = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "accounts_users"
        ordering = ["-created_at"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def first_name(self):
        return self.full_name.split()[0] if self.full_name else ""


class PriceAlert(models.Model):
    """User-configured price alerts for specific tickers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="price_alerts"
    )
    ticker = models.CharField(max_length=20)
    alert_type = models.CharField(
        max_length=10,
        choices=[
            ("above", "Price Above"),
            ("below", "Price Below"),
            ("change_pct", "% Change"),
        ],
    )
    threshold = models.DecimalField(max_digits=18, decimal_places=4)
    is_active = models.BooleanField(default=True)
    triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_price_alerts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.ticker} {self.alert_type} {self.threshold}"


class Notification(models.Model):
    """In-app notifications for users."""

    class NotificationType(models.TextChoices):
        PRICE_ALERT = "price_alert", "Price Alert"
        REBALANCE = "rebalance", "Rebalance Required"
        TAX_HARVEST = "tax_harvest", "Tax Harvest Opportunity"
        GOAL_MILESTONE = "goal_milestone", "Goal Milestone"
        SYSTEM = "system", "System"
        WEEKLY_DIGEST = "weekly_digest", "Weekly Digest"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=20, choices=NotificationType.choices
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_notifications"
        ordering = ["-created_at"]

    def mark_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "read_at"])
