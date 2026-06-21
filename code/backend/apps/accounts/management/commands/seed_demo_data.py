"""
Management command: python manage.py seed_demo_data
Creates a demo user with portfolios, holdings, goals, and sample transactions.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

DEMO_HOLDINGS = [
    ("AAPL", "Apple Inc.", "equity", 15, 165.00),
    ("MSFT", "Microsoft Corp.", "equity", 10, 290.00),
    ("GOOGL", "Alphabet Inc.", "equity", 5, 140.00),
    ("AMZN", "Amazon.com Inc.", "equity", 8, 175.00),
    ("BND", "Vanguard Total Bond Market ETF", "fixed_income", 50, 72.00),
    ("VNQ", "Vanguard Real Estate ETF", "real_estate", 20, 85.00),
    ("GLD", "SPDR Gold Shares", "commodity", 10, 180.00),
]

DEMO_GOALS = [
    {
        "name": "Retirement Fund",
        "goal_type": "retirement",
        "target_amount": Decimal("2000000"),
        "current_amount": Decimal("150000"),
        "monthly_contribution": Decimal("3000"),
        "target_date": date.today() + timedelta(days=365 * 25),
        "expected_return": Decimal("0.07"),
    },
    {
        "name": "House Down Payment",
        "goal_type": "house",
        "target_amount": Decimal("100000"),
        "current_amount": Decimal("25000"),
        "monthly_contribution": Decimal("1500"),
        "target_date": date.today() + timedelta(days=365 * 4),
        "expected_return": Decimal("0.05"),
    },
]


class Command(BaseCommand):
    help = "Seed the database with demo user, portfolios, holdings, and goals."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo@quantumwealth.ai")
        parser.add_argument("--password", default="Demo1234!")
        parser.add_argument(
            "--force", action="store_true", help="Delete existing demo user first"
        )

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.portfolio.models import (
            FinancialGoal,
            Holding,
            Portfolio,
            Transaction,
            TransactionType,
        )

        email = options["email"]

        if options["force"]:
            User.objects.filter(email=email).delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted existing demo user: {email}")
            )

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": "Demo Investor",
                "risk_profile": "moderate",
                "risk_score": 60,
                "is_verified": True,
                "annual_income": Decimal("150000"),
                "net_worth": Decimal("500000"),
                "tax_bracket_pct": Decimal("22.00"),
                "investment_horizon_years": 20,
            },
        )
        if created:
            user.set_password(options["password"])
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created demo user: {email}"))
        else:
            self.stdout.write(f"Demo user already exists: {email}")

        # Portfolio 1: Growth portfolio
        portfolio, _ = Portfolio.objects.get_or_create(
            user=user,
            name="Growth Portfolio",
            defaults={
                "description": "Diversified equity-focused portfolio",
                "cash_balance": Decimal("5000"),
                "target_allocation": {
                    t: round(1 / len(DEMO_HOLDINGS), 4) for t, *_ in DEMO_HOLDINGS
                },
                "benchmark_ticker": "SPY",
            },
        )

        total_value = portfolio.cash_balance
        for ticker, name, asset_class, qty, price in DEMO_HOLDINGS:
            pnl_factor = random.uniform(-0.15, 0.35)
            current_price = price * (1 + pnl_factor)
            mv = Decimal(str(qty)) * Decimal(str(round(current_price, 4)))
            total_value += mv
            Holding.objects.update_or_create(
                portfolio=portfolio,
                ticker=ticker,
                defaults={
                    "name": name,
                    "asset_class": asset_class,
                    "quantity": Decimal(str(qty)),
                    "average_cost": Decimal(str(price)),
                    "current_price": Decimal(str(round(current_price, 4))),
                    "market_value": mv,
                    "unrealized_pnl": mv - Decimal(str(qty)) * Decimal(str(price)),
                    "price_updated_at": timezone.now(),
                },
            )

        portfolio.total_value = total_value
        portfolio.save()

        # Recalculate weights
        for h in portfolio.holdings.all():
            h.weight = h.market_value / total_value
            h.save(update_fields=["weight"])

        # Sample transactions
        if not portfolio.transactions.exists():
            for ticker, _, _, qty, price in DEMO_HOLDINGS[:3]:
                Transaction.objects.create(
                    portfolio=portfolio,
                    ticker=ticker,
                    transaction_type=TransactionType.BUY,
                    quantity=Decimal(str(qty)),
                    price=Decimal(str(price)),
                    amount=Decimal(str(qty)) * Decimal(str(price)),
                    fees=Decimal("0"),
                    notes="Demo purchase",
                )
            Transaction.objects.create(
                portfolio=portfolio,
                transaction_type=TransactionType.DEPOSIT,
                amount=Decimal("50000"),
                notes="Initial deposit",
            )

        # Financial goals
        for goal_data in DEMO_GOALS:
            FinancialGoal.objects.get_or_create(
                user=user, name=goal_data["name"], defaults=goal_data
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDemo data seeded successfully!\n"
                f"   Login: {email} / {options['password']}\n"
                f"   Portfolio: {portfolio.name} (${float(portfolio.total_value):,.2f})\n"
                f"   Holdings: {portfolio.holdings.count()}\n"
                f"   Goals: {user.goals.count()}\n"
            )
        )
