"""Advisor service — goal planning, rebalancing, recommendations."""

import logging
from datetime import date, datetime, timezone

logger = logging.getLogger("apps.advisor")

RISK_RETURN_MAP = {
    "conservative": {"mu": 0.045, "sigma": 0.060},
    "moderate_conservative": {"mu": 0.060, "sigma": 0.090},
    "moderate": {"mu": 0.075, "sigma": 0.120},
    "moderate_aggressive": {"mu": 0.090, "sigma": 0.150},
    "aggressive": {"mu": 0.110, "sigma": 0.190},
}

SUGGESTED_PORTFOLIOS = {
    "retirement": {"VTI": 0.40, "VXUS": 0.20, "BND": 0.30, "TIP": 0.10},
    "education": {"VTI": 0.50, "VXUS": 0.15, "BND": 0.25, "VTIP": 0.10},
    "house": {"VTI": 0.30, "BND": 0.40, "SHY": 0.20, "CASH": 0.10},
    "emergency_fund": {"SHY": 0.40, "SGOV": 0.40, "CASH": 0.20},
    "vacation": {"VTI": 0.50, "BND": 0.30, "CASH": 0.20},
    "custom": {"VTI": 0.60, "BND": 0.30, "GLD": 0.10},
}


class AdvisorService:

    @staticmethod
    def generate_goal_plan(
        goal_type: str,
        target_amount: float,
        current_savings: float,
        monthly_contribution: float,
        target_date,
        expected_return: float = 0.075,
        inflation_rate: float = 0.03,
        inflation_adjusted: bool = True,
    ) -> dict:
        """Generate a comprehensive goal attainment plan with milestones."""
        from ai_models.robo_advisor import plan_goal

        # Normalize target_date to datetime
        if isinstance(target_date, date) and not isinstance(target_date, datetime):
            target_date = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                tzinfo=timezone.utc,
            )

        return plan_goal(
            goal_type=goal_type,
            target_amount=target_amount,
            current_savings=current_savings,
            monthly_contribution=monthly_contribution,
            target_date=target_date,
            inflation_rate=inflation_rate,
            expected_return=expected_return,
            inflation_adjusted=inflation_adjusted,
        )

    @staticmethod
    def compute_rebalance(
        portfolio,
        method: str = "threshold",
        drift_threshold: float = 0.05,
        min_trade_value: float = 100.0,
    ) -> dict:
        """Compute rebalancing trades to restore target allocation."""
        from ai_models.robo_advisor import compute_rebalance

        if not portfolio.target_allocation:
            return {"error": "No target allocation set for this portfolio."}

        holdings_data = [
            {
                "ticker": h.ticker,
                "current_weight": float(h.weight),
                "market_value": float(h.market_value),
                "average_cost": float(h.average_cost),
                "current_price": float(h.current_price),
            }
            for h in portfolio.holdings.all()
        ]

        return compute_rebalance(
            holdings=holdings_data,
            target_allocation=portfolio.target_allocation,
            portfolio_value=float(portfolio.total_value),
            drift_threshold=drift_threshold,
            min_trade_value=min_trade_value,
        )

    @staticmethod
    def get_recommendations(portfolio) -> dict:
        """Generate actionable AI-powered recommendations for the portfolio."""
        holdings = list(portfolio.holdings.all())
        if not holdings:
            return {
                "recommendations": [],
                "summary": "Add holdings to receive recommendations.",
            }

        recommendations = []

        # Check for concentration risk
        for h in holdings:
            weight = float(h.weight)
            if weight > 0.40:
                recommendations.append(
                    {
                        "type": "concentration_risk",
                        "severity": "high",
                        "ticker": h.ticker,
                        "message": f"{h.ticker} represents {weight:.1%} of your portfolio. Consider trimming to <40% to reduce concentration risk.",
                        "action": "REDUCE",
                    }
                )
            elif weight > 0.25:
                recommendations.append(
                    {
                        "type": "concentration_risk",
                        "severity": "medium",
                        "ticker": h.ticker,
                        "message": f"{h.ticker} represents {weight:.1%} of your portfolio.",
                        "action": "MONITOR",
                    }
                )

        # Check for missing asset classes
        asset_classes = {h.asset_class for h in holdings}
        if "fixed_income" not in asset_classes and len(holdings) > 2:
            recommendations.append(
                {
                    "type": "diversification",
                    "severity": "medium",
                    "message": "No fixed income holdings detected. Consider adding bonds (BND, AGG) for stability.",
                    "action": "ADD",
                }
            )
        if "real_estate" not in asset_classes and len(holdings) > 3:
            recommendations.append(
                {
                    "type": "diversification",
                    "severity": "low",
                    "message": "No real estate exposure. REITs (VNQ) can provide inflation protection.",
                    "action": "CONSIDER",
                }
            )

        # Tax-loss harvesting opportunity check
        harvestable = [h for h in holdings if float(h.unrealized_pnl) < -100]
        if harvestable:
            total_loss = sum(float(h.unrealized_pnl) for h in harvestable)
            recommendations.append(
                {
                    "type": "tax_loss_harvest",
                    "severity": "medium",
                    "message": f"${abs(total_loss):,.0f} in harvestable losses across {len(harvestable)} positions. Review tax optimization.",
                    "action": "HARVEST",
                    "tickers": [h.ticker for h in harvestable],
                }
            )

        # Check cash drag
        total_value = float(portfolio.total_value)
        cash_pct = float(portfolio.cash_balance) / total_value if total_value > 0 else 0
        if cash_pct > 0.10:
            recommendations.append(
                {
                    "type": "cash_drag",
                    "severity": "medium",
                    "message": f"Cash is {cash_pct:.1%} of portfolio. Excess cash may reduce long-term returns.",
                    "action": "DEPLOY",
                }
            )

        # Rebalancing check
        if portfolio.target_allocation:
            max_drift = max(
                (
                    abs(
                        float(h.weight)
                        - portfolio.target_allocation.get(h.ticker, float(h.weight))
                    )
                    for h in holdings
                ),
                default=0,
            )
            if max_drift > 0.05:
                recommendations.append(
                    {
                        "type": "rebalancing",
                        "severity": "medium",
                        "message": f"Portfolio has drifted {max_drift:.1%} from target. Consider rebalancing.",
                        "action": "REBALANCE",
                    }
                )

        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(
            key=lambda r: severity_order.get(r.get("severity", "low"), 3)
        )

        return {
            "portfolio_id": str(portfolio.id),
            "portfolio_value": total_value,
            "recommendations": recommendations,
            "summary": f"{len(recommendations)} recommendations found.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def get_allocation_drift(portfolio) -> dict:
        """Compute current allocation vs target for each holding."""
        if not portfolio.target_allocation:
            return {"error": "No target allocation defined."}

        drift_data = []
        for h in portfolio.holdings.all():
            current_w = float(h.weight)
            target_w = float(portfolio.target_allocation.get(h.ticker, current_w))
            drift = current_w - target_w
            drift_data.append(
                {
                    "ticker": h.ticker,
                    "current_weight": round(current_w, 4),
                    "target_weight": round(target_w, 4),
                    "drift": round(drift, 4),
                    "drift_pct": round(drift * 100, 2),
                    "needs_action": abs(drift) >= 0.05,
                }
            )

        total_drift = sum(abs(d["drift"]) for d in drift_data)
        return {
            "portfolio_id": str(portfolio.id),
            "drift_data": drift_data,
            "total_drift": round(total_drift, 4),
            "needs_rebalancing": total_drift > 0.05,
        }
