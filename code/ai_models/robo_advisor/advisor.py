"""
QuantumWealth AI Engine — Robo Advisor
Goal-based financial planning, rebalancing engine, allocation recommendations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger("ai_engine.robo_advisor")

SUGGESTED_PORTFOLIOS = {
    "retirement": {"VTI": 0.40, "VXUS": 0.20, "BND": 0.30, "TIP": 0.10},
    "education": {"VTI": 0.50, "VXUS": 0.15, "BND": 0.25, "VTIP": 0.10},
    "house": {"VTI": 0.30, "BND": 0.40, "SHY": 0.20, "CASH": 0.10},
    "emergency_fund": {"SHY": 0.40, "SGOV": 0.40, "CASH": 0.20},
    "vacation": {"VTI": 0.50, "BND": 0.30, "CASH": 0.20},
    "custom": {"VTI": 0.60, "BND": 0.30, "GLD": 0.10},
}


def _future_value(pv: float, pmt: float, rate_annual: float, years: float) -> float:
    r = rate_annual / 12
    n = years * 12
    if r <= 0:
        return pv + pmt * n
    fv_pv = pv * (1 + r) ** n
    fv_pmt = pmt * (((1 + r) ** n - 1) / r)
    return fv_pv + fv_pmt


def _required_pmt(target: float, pv: float, rate_annual: float, years: float) -> float:
    r = rate_annual / 12
    n = years * 12
    fv_pv = pv * (1 + r) ** n
    remaining = target - fv_pv
    if remaining <= 0:
        return 0.0
    if r == 0:
        return remaining / n
    return remaining / (((1 + r) ** n - 1) / r)


def plan_goal(
    goal_type: str,
    target_amount: float,
    current_savings: float,
    monthly_contribution: float,
    target_date: datetime,
    inflation_rate: float = 0.03,
    expected_return: float = 0.075,
    inflation_adjusted: bool = True,
) -> Dict:
    now = datetime.now(timezone.utc)
    if target_date.tzinfo is None:
        target_date = target_date.replace(tzinfo=timezone.utc)
    years = max(0.5, (target_date - now).days / 365.25)

    real_target = (
        target_amount * (1 + inflation_rate) ** years
        if inflation_adjusted
        else target_amount
    )
    real_rate = (
        ((1 + expected_return) / (1 + inflation_rate) - 1)
        if inflation_adjusted
        else expected_return
    )

    projected = _future_value(current_savings, monthly_contribution, real_rate, years)
    gap = real_target - projected
    prob_success = min(1.0, max(0.0, projected / real_target))
    required_contribution = _required_pmt(
        real_target, current_savings, real_rate, years
    )

    # Milestones at 25 / 50 / 75 %
    milestones = []
    for pct in [0.25, 0.50, 0.75, 1.00]:
        milestone_target = real_target * pct
        if current_savings >= milestone_target:
            milestones.append(
                {
                    "milestone": f"{int(pct*100)}%",
                    "status": "achieved",
                    "amount": round(milestone_target, 2),
                }
            )
        else:
            months = 0
            bal = current_savings
            while bal < milestone_target and months < 1200:
                bal = bal * (1 + real_rate / 12) + monthly_contribution
                months += 1
            milestones.append(
                {
                    "milestone": f"{int(pct*100)}%",
                    "status": "pending",
                    "amount": round(milestone_target, 2),
                    "estimated_months": months,
                    "estimated_years": round(months / 12, 1),
                }
            )

    # Scenario analysis
    scenarios = {}
    for label, ret_adj in [
        ("conservative", -0.02),
        ("base", 0.0),
        ("optimistic", +0.02),
    ]:
        adj_rate = max(0.01, real_rate + ret_adj)
        proj = _future_value(current_savings, monthly_contribution, adj_rate, years)
        scenarios[label] = {
            "expected_return_pct": round((real_rate + ret_adj) * 100, 1),
            "projected_value": round(proj, 2),
            "probability_of_success": round(min(1.0, max(0.0, proj / real_target)), 4),
        }

    return {
        "goal_type": goal_type,
        "inflation_adjusted_target": round(real_target, 2),
        "original_target": round(target_amount, 2),
        "projected_value": round(projected, 2),
        "probability_of_success": round(prob_success, 4),
        "recommended_monthly_contribution": round(required_contribution, 2),
        "current_monthly_contribution": round(monthly_contribution, 2),
        "contribution_gap": round(
            max(0, required_contribution - monthly_contribution), 2
        ),
        "suggested_portfolio": SUGGESTED_PORTFOLIOS.get(
            goal_type, SUGGESTED_PORTFOLIOS["custom"]
        ),
        "milestones": milestones,
        "scenarios": scenarios,
        "gap_analysis": {
            "gap_amount": round(gap, 2),
            "on_track": gap <= 0,
            "years_to_goal": round(years, 2),
            "inflation_adjusted": inflation_adjusted,
        },
    }


def compute_rebalance(
    holdings: List[Dict],
    target_allocation: Dict[str, float],
    portfolio_value: float,
    drift_threshold: float = 0.05,
    min_trade_value: float = 100.0,
) -> Dict:
    trades = []
    total_drift = 0.0

    for h in holdings:
        ticker = h["ticker"]
        curr_w = h["current_weight"]
        target_w = target_allocation.get(ticker, curr_w)
        drift = abs(curr_w - target_w)
        total_drift += drift

        if drift >= drift_threshold:
            action = "BUY" if curr_w < target_w else "SELL"
            trade_value = abs(curr_w - target_w) * portfolio_value
            if trade_value >= min_trade_value:
                price = h.get("current_price", 1.0) or 1.0
                unrealized = (h.get("current_price", 0) - h.get("average_cost", 0)) * (
                    h.get("market_value", 0) / max(h.get("current_price", 1), 0.01)
                )
                trades.append(
                    {
                        "ticker": ticker,
                        "action": action,
                        "current_weight": round(curr_w, 4),
                        "target_weight": round(target_w, 4),
                        "drift": round(drift, 4),
                        "drift_pct": round(drift * 100, 2),
                        "estimated_value": round(trade_value, 2),
                        "suggested_shares": round(trade_value / price, 4),
                        "tax_impact_est": (
                            round(max(0, unrealized * 0.20), 2)
                            if action == "SELL"
                            else 0.0
                        ),
                    }
                )

    # Sells first (free up cash), then buys sorted by size
    trades.sort(
        key=lambda t: (0 if t["action"] == "SELL" else 1, -t["estimated_value"])
    )

    total_trade_value = sum(t["estimated_value"] for t in trades)
    estimated_commission = round(total_trade_value * 0.0005, 2)  # 5bps estimate
    estimated_tax = round(sum(t.get("tax_impact_est", 0) for t in trades), 2)

    return {
        "needs_rebalancing": len(trades) > 0,
        "total_drift": round(total_drift, 4),
        "drift_threshold": drift_threshold,
        "trades": trades,
        "trade_count": len(trades),
        "total_trade_value": round(total_trade_value, 2),
        "estimated_commission": estimated_commission,
        "estimated_tax_impact": estimated_tax,
        "net_cost": round(estimated_commission + estimated_tax, 2),
    }
