"""
Shared helper factories for the QuantumWealth backend test suite.

All Django model imports are kept inside function bodies so this module
is safe to import before django.setup() runs.  pytest-django calls
django.setup() automatically before any test is collected.
"""

from decimal import Decimal


def make_user(
    email="test@quantumwealth.ai",
    password="SecurePass123!",
    full_name="Test Investor",
    risk_profile="moderate",
    risk_score=60,
    tax_bracket_pct=Decimal("22.00"),
    is_verified=True,
    **kwargs,
):
    from apps.accounts.models import User

    return User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name,
        risk_profile=risk_profile,
        risk_score=risk_score,
        tax_bracket_pct=tax_bracket_pct,
        is_verified=is_verified,
        **kwargs,
    )


def make_staff_user(email="staff@qw.ai", password="StaffPass123!"):
    from apps.accounts.models import User

    return User.objects.create_user(
        email=email,
        password=password,
        full_name="Staff Member",
        is_staff=True,
        is_verified=True,
    )


def auth_client(user):
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def anon_client():
    from rest_framework.test import APIClient

    return APIClient()


def make_portfolio(
    user,
    name="Test Portfolio",
    cash=Decimal("10000.00"),
    total_value=None,
    target_allocation=None,
    benchmark_ticker="SPY",
):
    from apps.portfolio.models import Portfolio

    return Portfolio.objects.create(
        user=user,
        name=name,
        cash_balance=cash,
        total_value=total_value if total_value is not None else cash,
        target_allocation=target_allocation or {},
        benchmark_ticker=benchmark_ticker,
    )


def add_holding(
    portfolio,
    ticker="AAPL",
    qty=Decimal("10"),
    price=Decimal("150.00"),
    asset_class="equity",
    name="",
    unrealized_pnl=None,
):
    from apps.portfolio.models import Holding

    market_value = qty * price
    pnl = unrealized_pnl if unrealized_pnl is not None else Decimal("0")

    holding = Holding.objects.create(
        portfolio=portfolio,
        ticker=ticker.upper(),
        name=name or ticker.upper(),
        asset_class=asset_class,
        quantity=qty,
        average_cost=price,
        current_price=price,
        market_value=market_value,
        unrealized_pnl=pnl,
    )

    # Recompute portfolio total value and weights
    portfolio.total_value = portfolio.cash_balance + sum(
        h.market_value for h in portfolio.holdings.all()
    )
    portfolio.save(update_fields=["total_value"])

    if portfolio.total_value > 0:
        for h in portfolio.holdings.all():
            h.weight = h.market_value / portfolio.total_value
            h.save(update_fields=["weight"])

    return portfolio.holdings.get(pk=holding.pk)


def add_transaction(
    portfolio,
    txn_type="deposit",
    amount=Decimal("1000.00"),
    ticker="",
    qty=None,
    price=None,
    fees=Decimal("0.00"),
    realized_gain=None,
    holding_period_days=None,
    is_long_term=None,
):
    from apps.portfolio.models import Transaction

    return Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=txn_type,
        amount=amount,
        ticker=ticker,
        quantity=qty,
        price=price,
        fees=fees,
        realized_gain=realized_gain,
        holding_period_days=holding_period_days,
        is_long_term=is_long_term,
    )


def make_goal(
    user,
    name="Retirement",
    goal_type="retirement",
    target_amount=Decimal("1000000.00"),
    current_amount=Decimal("50000.00"),
    monthly_contribution=Decimal("2000.00"),
    target_date_offset_days=365 * 25,
):
    from datetime import date, timedelta

    from apps.portfolio.models import FinancialGoal

    return FinancialGoal.objects.create(
        user=user,
        name=name,
        goal_type=goal_type,
        target_amount=target_amount,
        current_amount=current_amount,
        monthly_contribution=monthly_contribution,
        target_date=date.today() + timedelta(days=target_date_offset_days),
        expected_return=Decimal("0.07"),
    )


def make_snapshot(portfolio, date_offset_days=0, total_value=None):
    from datetime import date, timedelta

    from apps.portfolio.models import PortfolioSnapshot

    snap_date = date.today() - timedelta(days=date_offset_days)
    return PortfolioSnapshot.objects.create(
        portfolio=portfolio,
        date=snap_date,
        total_value=total_value or portfolio.total_value,
        cash_balance=portfolio.cash_balance,
        holdings_value=(total_value or portfolio.total_value) - portfolio.cash_balance,
        holdings_snapshot={},
    )


def make_notification(
    user,
    notification_type="system",
    title="Test notification",
    message="Test message body",
    is_read=False,
):
    from apps.accounts.models import Notification

    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        is_read=is_read,
    )


def make_price_alert(
    user, ticker="AAPL", alert_type="above", threshold=Decimal("200.00")
):
    from apps.accounts.models import PriceAlert

    return PriceAlert.objects.create(
        user=user,
        ticker=ticker,
        alert_type=alert_type,
        threshold=threshold,
    )
