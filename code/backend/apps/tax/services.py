"""
Tax Optimizer Service — tax-loss harvesting, gain/loss reporting, asset location.
Fully implemented with real holding-period tracking from transaction history.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

logger = logging.getLogger("apps.tax")

# Wash-sale compliant substitutes (must be similar but NOT substantially identical)
WASH_SALE_SUBSTITUTES = {
    "SPY": ["IVV", "VOO", "SPLG"],
    "QQQ": ["QQQM", "ONEQ", "QQQJ"],
    "IWM": ["VB", "IJR", "SCHA"],
    "GLD": ["IAU", "SGOL", "GLDM"],
    "TLT": ["IEF", "VGLT", "SPTL"],
    "AGG": ["BND", "SCHZ", "IUSB"],
    "VTI": ["ITOT", "SCHB", "FZROX"],
    "EFA": ["VEA", "IEFA", "SCHF"],
    "EEM": ["VWO", "IEMG", "SCHE"],
    "VNQ": ["SCHH", "IYR", "RWR"],
    "XLK": ["VGT", "FTEC", "IYW"],
    "BND": ["AGG", "SCHZ", "IUSB"],
    "VB": ["IWM", "IJR", "SCHA"],
    "ARKK": ["ARKW", "ARKG"],
}

# Per-asset-class heuristics for asset location
LOCATION_RULES = {
    "equity": (
        "taxable",
        "Qualified dividends taxed at preferential rates in taxable accounts.",
    ),
    "fixed_income": (
        "tax_advantaged",
        "Interest income taxed as ordinary income — shelter in IRA/401k.",
    ),
    "real_estate": (
        "tax_advantaged",
        "REIT dividends fully taxable as ordinary income — shelter in IRA/401k.",
    ),
    "commodity": (
        "taxable",
        "Low yield and capital-gains-driven — suitable for taxable accounts.",
    ),
    "crypto": (
        "tax_advantaged",
        "High volatility creates large taxable events — defer in Roth IRA if possible.",
    ),
    "cash": ("taxable", "Minimal tax impact; fine in taxable accounts."),
    "alternative": (
        "tax_advantaged",
        "Complex tax treatment — prefer sheltered accounts.",
    ),
}


class TaxService:

    @staticmethod
    def _get_portfolio(portfolio_id, user):
        from apps.portfolio.models import Portfolio
        from django.shortcuts import get_object_or_404

        return get_object_or_404(
            Portfolio.objects.prefetch_related("holdings", "transactions"),
            id=portfolio_id,
            user=user,
            is_active=True,
        )

    @classmethod
    def find_harvest_opportunities(cls, portfolio_id, user) -> dict:
        """Identify positions with unrealized losses suitable for tax-loss harvesting."""
        portfolio = cls._get_portfolio(portfolio_id, user)
        user_tax_rate = float(user.tax_bracket_pct) / 100  # e.g. 0.37
        cap_gains_rate = min(user_tax_rate, 0.20)  # long-term cap gains max 20%

        opportunities = []
        for holding in portfolio.holdings.all():
            unrealized_pnl = float(holding.unrealized_pnl)
            if unrealized_pnl >= -50:
                continue  # only meaningful losses

            market_value = float(holding.market_value)
            cost_basis = float(holding.quantity * holding.average_cost)
            loss_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0

            # Compute holding period from first BUY transaction
            from apps.portfolio.models import TransactionType

            first_buy = (
                portfolio.transactions.filter(
                    ticker=holding.ticker, transaction_type=TransactionType.BUY
                )
                .order_by("executed_at")
                .first()
            )
            holding_period_days = None
            is_long_term = None
            if first_buy:
                holding_period_days = (
                    datetime.now(timezone.utc) - first_buy.executed_at
                ).days
                is_long_term = holding_period_days >= 365

            # Tax savings depends on whether it offsets short- or long-term gains
            effective_rate = cap_gains_rate if is_long_term else user_tax_rate
            estimated_tax_savings = abs(unrealized_pnl) * effective_rate

            substitutes = WASH_SALE_SUBSTITUTES.get(holding.ticker, [])

            opportunities.append(
                {
                    "ticker": holding.ticker,
                    "name": holding.name or holding.ticker,
                    "quantity": float(holding.quantity),
                    "current_price": float(holding.current_price),
                    "average_cost": float(holding.average_cost),
                    "market_value": round(market_value, 2),
                    "unrealized_loss": round(unrealized_pnl, 2),
                    "loss_pct": round(loss_pct, 2),
                    "holding_period_days": holding_period_days,
                    "is_long_term": is_long_term,
                    "estimated_tax_savings": round(estimated_tax_savings, 2),
                    "effective_tax_rate": round(effective_rate * 100, 1),
                    "wash_sale_substitutes": substitutes,
                    "wash_sale_window_days": 30,
                }
            )

        opportunities.sort(key=lambda x: x["unrealized_loss"])

        return {
            "portfolio_id": str(portfolio_id),
            "tax_year": datetime.now().year,
            "opportunities": opportunities,
            "total_harvestable_losses": round(
                sum(o["unrealized_loss"] for o in opportunities), 2
            ),
            "estimated_total_tax_savings": round(
                sum(o["estimated_tax_savings"] for o in opportunities), 2
            ),
            "user_tax_bracket_pct": float(user.tax_bracket_pct),
            "note": (
                "Sell harvested positions and immediately buy substitutes. "
                "Do NOT repurchase the original security within 30 days before or after the sale "
                "(IRS wash-sale rule)."
            ),
        }

    @classmethod
    def gain_loss_report(cls, portfolio_id, user, tax_year: int) -> dict:
        """Generate realized gain/loss report for a tax year with short/long-term breakdown."""
        portfolio = cls._get_portfolio(portfolio_id, user)
        from apps.portfolio.models import TransactionType

        sell_txns = portfolio.transactions.filter(
            transaction_type=TransactionType.SELL,
            executed_at__year=tax_year,
        )

        short_term_gain = Decimal("0")
        short_term_loss = Decimal("0")
        long_term_gain = Decimal("0")
        long_term_loss = Decimal("0")
        realized_events = []

        for txn in sell_txns:
            gain = txn.realized_gain or Decimal("0")
            is_long = txn.is_long_term

            if is_long:
                if gain >= 0:
                    long_term_gain += gain
                else:
                    long_term_loss += gain
            else:
                if gain >= 0:
                    short_term_gain += gain
                else:
                    short_term_loss += gain

            realized_events.append(
                {
                    "ticker": txn.ticker,
                    "date": txn.executed_at.date().isoformat(),
                    "proceeds": float(txn.amount),
                    "cost_basis": float(txn.cost_basis or 0),
                    "gain_loss": float(gain),
                    "term": "long" if is_long else "short",
                    "holding_period_days": txn.holding_period_days,
                }
            )

        user_rate = float(user.tax_bracket_pct) / 100
        st_rate = user_rate
        lt_rate = min(user_rate, 0.20)

        net_st = float(short_term_gain + short_term_loss)
        net_lt = float(long_term_gain + long_term_loss)
        estimated_tax = max(0, net_st) * st_rate + max(0, net_lt) * lt_rate

        return {
            "tax_year": tax_year,
            "short_term": {
                "gains": float(short_term_gain),
                "losses": float(short_term_loss),
                "net": round(net_st, 2),
                "tax_rate_pct": round(st_rate * 100, 1),
            },
            "long_term": {
                "gains": float(long_term_gain),
                "losses": float(long_term_loss),
                "net": round(net_lt, 2),
                "tax_rate_pct": round(lt_rate * 100, 1),
            },
            "total_net_gain": round(net_st + net_lt, 2),
            "estimated_tax_liability": round(estimated_tax, 2),
            "realized_events": realized_events,
            "event_count": len(realized_events),
        }

    @classmethod
    def recommend_asset_location(cls, portfolio_id, user) -> dict:
        """Recommend optimal asset placement across taxable vs tax-advantaged accounts."""
        portfolio = cls._get_portfolio(portfolio_id, user)
        recommendations = []

        tax_advantaged_value = 0.0
        taxable_value = 0.0

        for holding in portfolio.holdings.all():
            asset_class = holding.asset_class
            location, rationale = LOCATION_RULES.get(
                asset_class, ("taxable", "Default: suitable for taxable accounts.")
            )
            value = float(holding.market_value)
            if location == "tax_advantaged":
                tax_advantaged_value += value
            else:
                taxable_value += value

            recommendations.append(
                {
                    "ticker": holding.ticker,
                    "name": holding.name or holding.ticker,
                    "asset_class": asset_class,
                    "market_value": round(value, 2),
                    "recommended_account": location,
                    "rationale": rationale,
                    "annual_tax_drag_est": round(
                        (
                            value * 0.015
                            if location == "tax_advantaged"
                            else value * 0.005
                        ),
                        2,
                    ),
                }
            )

        recommendations.sort(
            key=lambda r: (r["recommended_account"], -r["market_value"])
        )

        return {
            "portfolio_id": str(portfolio_id),
            "recommendations": recommendations,
            "summary": {
                "tax_advantaged_value": round(tax_advantaged_value, 2),
                "taxable_value": round(taxable_value, 2),
                "estimated_annual_tax_drag": round(
                    sum(r["annual_tax_drag_est"] for r in recommendations), 2
                ),
            },
            "priority": (
                "Move fixed income and REITs to tax-advantaged accounts first "
                "for maximum lifetime tax efficiency."
            ),
        }

    @classmethod
    def wash_sale_check(
        cls, portfolio_id, user, ticker: str, sell_date_str: str
    ) -> dict:
        """Check for wash-sale violations around a proposed sell date."""
        from datetime import date, timedelta

        portfolio = cls._get_portfolio(portfolio_id, user)
        from apps.portfolio.models import TransactionType

        try:
            sell_date = date.fromisoformat(sell_date_str)
        except ValueError:
            return {"error": "Invalid sell_date. Use YYYY-MM-DD."}

        window_start = datetime(
            sell_date.year, sell_date.month, sell_date.day, tzinfo=timezone.utc
        ) - timedelta(days=30)
        window_end = datetime(
            sell_date.year, sell_date.month, sell_date.day, tzinfo=timezone.utc
        ) + timedelta(days=30)

        buys_in_window = portfolio.transactions.filter(
            ticker=ticker.upper(),
            transaction_type=TransactionType.BUY,
            executed_at__gte=window_start,
            executed_at__lte=window_end,
        )

        violations = [
            {
                "date": t.executed_at.date().isoformat(),
                "quantity": float(t.quantity or 0),
                "price": float(t.price or 0),
            }
            for t in buys_in_window
        ]

        is_wash_sale = len(violations) > 0
        return {
            "ticker": ticker.upper(),
            "proposed_sell_date": sell_date_str,
            "is_wash_sale": is_wash_sale,
            "violations": violations,
            "message": (
                "Wash-sale violation detected. The loss will be disallowed by the IRS."
                if is_wash_sale
                else "No wash-sale violations detected for this sell date."
            ),
            "substitutes": WASH_SALE_SUBSTITUTES.get(ticker.upper(), []),
        }
