"""Portfolio service — CRUD, optimization, performance, snapshots."""

import logging
from decimal import Decimal

from ai_models.portfolio_optimizer import PortfolioOptimizer
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Holding, Portfolio, PortfolioSnapshot, Transaction

logger = logging.getLogger("apps.portfolio")


class PortfolioService:

    @staticmethod
    def get_portfolio_for_user(portfolio_id, user):
        return get_object_or_404(Portfolio, id=portfolio_id, user=user, is_active=True)

    @staticmethod
    @db_transaction.atomic
    def upsert_holding(
        portfolio,
        ticker: str,
        quantity: Decimal,
        average_cost: Decimal,
        name: str = "",
        asset_class: str = "equity",
    ) -> Holding:
        """Add a new holding or update existing one with weighted-average cost."""
        ticker = ticker.upper()
        holding, created = Holding.objects.get_or_create(
            portfolio=portfolio,
            ticker=ticker,
            defaults={
                "name": name,
                "asset_class": asset_class,
                "quantity": quantity,
                "average_cost": average_cost,
                "current_price": average_cost,
                "market_value": quantity * average_cost,
            },
        )
        if not created:
            total_qty = holding.quantity + quantity
            holding.average_cost = (
                holding.quantity * holding.average_cost + quantity * average_cost
            ) / total_qty
            holding.quantity = total_qty
            holding.recalculate()
            holding.save()
        PortfolioService.recalculate_portfolio(portfolio)
        return holding

    @staticmethod
    @db_transaction.atomic
    def record_transaction(portfolio, data: dict) -> Transaction:
        """Record a transaction and update portfolio state accordingly."""
        # FIX: cast to plain str so comparisons work in all Python versions
        # (Python 3.11+ changed TextChoices equality semantics)
        txn_type = str(data["transaction_type"])
        ticker = data.get("ticker", "") or ""
        ticker = ticker.upper()
        quantity = data.get("quantity")
        price = data.get("price")
        amount = data["amount"]
        fees = data.get("fees", Decimal("0")) or Decimal("0")

        txn = Transaction.objects.create(
            portfolio=portfolio,
            ticker=ticker,
            transaction_type=txn_type,
            quantity=quantity,
            price=price,
            amount=amount,
            fees=fees,
            notes=data.get("notes", "") or "",
        )

        # Update portfolio cash / holdings
        # Use plain string comparisons to avoid TextChoices enum issues
        if txn_type == "deposit":
            portfolio.cash_balance += amount
            portfolio.save(update_fields=["cash_balance", "updated_at"])

        elif txn_type == "withdrawal":
            portfolio.cash_balance -= amount
            portfolio.save(update_fields=["cash_balance", "updated_at"])

        elif txn_type == "buy" and ticker and quantity and price:
            total_cost = quantity * price + fees
            portfolio.cash_balance -= total_cost
            # FIX: explicitly save cash_balance BEFORE calling upsert_holding.
            # recalculate_portfolio only saves total_value, not cash_balance.
            portfolio.save(update_fields=["cash_balance", "updated_at"])
            PortfolioService.upsert_holding(portfolio, ticker, quantity, price)

        elif txn_type == "sell" and ticker and quantity and price:
            try:
                holding = Holding.objects.get(portfolio=portfolio, ticker=ticker)

                # Realized gain = (sell price - avg cost) * qty
                realized = (price - holding.average_cost) * quantity

                # Holding period from first BUY transaction
                first_buy = (
                    Transaction.objects.filter(
                        portfolio=portfolio,
                        ticker=ticker,
                        transaction_type="buy",
                    )
                    .order_by("executed_at")
                    .first()
                )

                holding_days = None
                is_long_term = None
                if first_buy:
                    holding_days = (timezone.now() - first_buy.executed_at).days
                    is_long_term = holding_days >= 365

                # Persist tax metadata to the sell transaction
                txn.realized_gain = realized
                txn.holding_period_days = holding_days
                txn.is_long_term = is_long_term
                txn.cost_basis = holding.average_cost * quantity
                txn.save(
                    update_fields=[
                        "realized_gain",
                        "holding_period_days",
                        "is_long_term",
                        "cost_basis",
                    ]
                )

                # Reduce or remove the holding
                holding.quantity -= quantity
                if holding.quantity <= Decimal("0"):
                    holding.delete()
                else:
                    holding.recalculate()
                    holding.save()

                # Update cash from sale proceeds
                portfolio.cash_balance += amount - fees
                portfolio.save(update_fields=["cash_balance", "updated_at"])

            except Holding.DoesNotExist:
                logger.warning(
                    "Sell for non-existent holding %s in portfolio %s",
                    ticker,
                    portfolio.id,
                )

        elif txn_type == "dividend" and ticker:
            portfolio.cash_balance += amount
            portfolio.save(update_fields=["cash_balance", "updated_at"])

        # Always recompute portfolio total_value and weights
        PortfolioService.recalculate_portfolio(portfolio)
        return txn

    @staticmethod
    def recalculate_portfolio(portfolio: Portfolio):
        """Recompute total_value and holding weights from current prices and cash."""
        # Re-fetch portfolio from DB to get the latest cash_balance
        portfolio.refresh_from_db()
        holdings = list(portfolio.holdings.all())
        total = portfolio.cash_balance
        for h in holdings:
            h.market_value = h.quantity * h.current_price
            h.unrealized_pnl = h.market_value - h.quantity * h.average_cost
            cost = h.quantity * h.average_cost
            h.unrealized_pnl_pct = (
                (h.unrealized_pnl / cost * 100) if cost > 0 else Decimal("0")
            )
            total += h.market_value
        portfolio.total_value = total
        if total > 0:
            for h in holdings:
                h.weight = h.market_value / total
        else:
            for h in holdings:
                h.weight = Decimal("0")
        for h in holdings:
            h.save(
                update_fields=[
                    "market_value",
                    "unrealized_pnl",
                    "unrealized_pnl_pct",
                    "weight",
                ]
            )
        portfolio.save(update_fields=["total_value", "updated_at"])

    @staticmethod
    def optimize(
        portfolio: Portfolio,
        strategy: str,
        risk_tolerance: float,
        target_return=None,
        max_weight: float = 0.40,
        constraints: dict = None,
    ):
        """Run AI portfolio optimization."""
        tickers = list(portfolio.holdings.values_list("ticker", flat=True))
        if not tickers:
            return {"error": "Portfolio has no holdings to optimize."}

        current_weights = {h.ticker: float(h.weight) for h in portfolio.holdings.all()}
        optimizer = PortfolioOptimizer()
        return optimizer.optimize(
            tickers=tickers,
            strategy=strategy,
            current_weights=current_weights,
            risk_tolerance=risk_tolerance,
            target_return=target_return,
            max_weight=max_weight,
            constraints=constraints or {},
        )

    @staticmethod
    def get_performance(portfolio: Portfolio) -> dict:
        """Full risk/performance report via AI engine."""
        tickers = list(portfolio.holdings.values_list("ticker", flat=True))
        weights = [float(h.weight) for h in portfolio.holdings.all()]
        if not tickers:
            return {"error": "No holdings for performance computation."}
        from ai_models.risk_engine import RiskEngine

        engine = RiskEngine()
        return engine.full_report(tickers, weights, float(portfolio.total_value))

    @staticmethod
    def take_snapshot(portfolio: Portfolio):
        """Record a daily portfolio value snapshot (idempotent — upserts by date)."""
        today = timezone.localdate()
        yesterday = (
            PortfolioSnapshot.objects.filter(portfolio=portfolio)
            .order_by("-date")
            .first()
        )

        daily_return = None
        if yesterday and yesterday.total_value > 0:
            daily_return = (
                (portfolio.total_value - yesterday.total_value)
                / yesterday.total_value
                * 100
            )

        holdings_snapshot = {
            h.ticker: {
                "quantity": float(h.quantity),
                "price": float(h.current_price),
                "value": float(h.market_value),
                "weight": float(h.weight),
            }
            for h in portfolio.holdings.all()
        }

        PortfolioSnapshot.objects.update_or_create(
            portfolio=portfolio,
            date=today,
            defaults={
                "total_value": portfolio.total_value,
                "cash_balance": portfolio.cash_balance,
                "holdings_value": portfolio.total_value - portfolio.cash_balance,
                "daily_return_pct": daily_return,
                "holdings_snapshot": holdings_snapshot,
            },
        )
