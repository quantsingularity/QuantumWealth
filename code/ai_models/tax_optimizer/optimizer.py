"""
QuantumWealth AI Models -- Tax Optimizer
========================================
Advanced tax optimization using dynamic programming and greedy heuristics:
  - Tax-loss harvesting scheduler with wash-sale calendar management
  - Optimal gain/loss matching (specific identification method)
  - Tax-efficient rebalancing (minimize gains while restoring target allocation)
  - After-tax return optimization with bracket-aware modeling
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List


logger = logging.getLogger("ai_models.tax_optimizer")

WASH_SALE_DAYS = 30

WASH_SALE_SUBSTITUTES: Dict[str, List[str]] = {
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
    "BND": ["AGG", "SCHZ", "IUSB"],
    "XLK": ["VGT", "FTEC", "IYW"],
}


class TaxOptimizer:
    """Advanced tax optimization for portfolio management."""

    def optimize_harvest_schedule(
        self,
        holdings: List[Dict],
        tax_rate_short: float = 0.37,
        tax_rate_long: float = 0.20,
        annual_gain_target: float = 0.0,
        min_loss_threshold: float = 500.0,
    ) -> Dict:
        """
        Schedule tax-loss harvesting to maximize after-tax return.
        Uses greedy approach: harvest largest losses first while
        respecting wash-sale constraints.

        Parameters
        ----------
        holdings          : list of dicts with ticker, unrealized_pnl, is_long_term, market_value
        tax_rate_short    : marginal short-term capital gains rate
        tax_rate_long     : long-term capital gains rate
        annual_gain_target: existing realized gains to offset (0 = no target)
        min_loss_threshold: minimum USD loss to consider harvesting
        """
        candidates = [
            h
            for h in holdings
            if float(h.get("unrealized_pnl", 0)) < -min_loss_threshold
        ]
        candidates.sort(key=lambda h: float(h.get("unrealized_pnl", 0)))

        harvest_plan = []
        total_offset = 0.0
        remaining_gain = annual_gain_target

        for holding in candidates:
            loss = abs(float(holding.get("unrealized_pnl", 0)))
            is_long = holding.get("is_long_term", False)
            rate = tax_rate_long if is_long else tax_rate_short
            tax_savings = loss * rate
            ticker = holding.get("ticker", "")
            substitutes = WASH_SALE_SUBSTITUTES.get(ticker, [])

            # Determine if harvesting is beneficial
            if remaining_gain > 0 or annual_gain_target == 0:
                harvest_plan.append(
                    {
                        "ticker": ticker,
                        "unrealized_loss": round(-loss, 2),
                        "holding_period": "long-term" if is_long else "short-term",
                        "applicable_tax_rate_pct": round(rate * 100, 1),
                        "estimated_tax_savings": round(tax_savings, 2),
                        "market_value": round(float(holding.get("market_value", 0)), 2),
                        "wash_sale_substitutes": substitutes,
                        "action": "SELL_AND_REPLACE",
                        "reinvest_in": (
                            substitutes[0] if substitutes else "HOLD_CASH_30_DAYS"
                        ),
                        "repurchase_after_date": str(
                            (
                                datetime.now(timezone.utc)
                                + timedelta(days=WASH_SALE_DAYS + 1)
                            ).date()
                        ),
                    }
                )
                total_offset += loss
                remaining_gain = max(0, remaining_gain - loss)

        return {
            "harvest_plan": harvest_plan,
            "summary": {
                "positions_to_harvest": len(harvest_plan),
                "total_losses_to_harvest": round(
                    -sum(h["unrealized_loss"] for h in harvest_plan), 2
                ),
                "estimated_total_tax_savings": round(
                    sum(h["estimated_tax_savings"] for h in harvest_plan), 2
                ),
                "gains_offset": round(min(total_offset, annual_gain_target), 2),
                "remaining_gains_after_harvest": round(
                    max(0, annual_gain_target - total_offset), 2
                ),
            },
            "notes": [
                "Sell harvested positions and immediately purchase designated substitutes.",
                f"Do not repurchase original security within {WASH_SALE_DAYS} days before or after sale.",
                "Keep records of all lots for specific identification cost basis method.",
                "Consult a tax advisor before executing harvest strategies.",
            ],
        }

    def optimize_rebalance_for_taxes(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        holdings: List[Dict],
        portfolio_value: float,
        tax_rate_short: float = 0.37,
        tax_rate_long: float = 0.20,
    ) -> Dict:
        """
        Generate tax-efficient rebalancing plan:
        1. Prioritize selling positions with losses first
        2. Defer selling positions with large gains
        3. Use cash inflows to buy underweight positions
        4. Recommend which lots to sell (FIFO vs specific ID)
        """
        holding_map = {h.get("ticker"): h for h in holdings}
        trades = []
        total_tax_cost = 0.0

        for ticker, target_w in target_weights.items():
            curr_w = current_weights.get(ticker, 0.0)
            diff = target_w - curr_w
            if abs(diff) < 0.005:
                continue

            trade_value = abs(diff) * portfolio_value
            action = "BUY" if diff > 0 else "SELL"
            h = holding_map.get(ticker, {})
            pnl = float(h.get("unrealized_pnl", 0))
            is_long = h.get("is_long_term", False)

            tax_cost = 0.0
            if action == "SELL" and pnl > 0:
                rate = tax_rate_long if is_long else tax_rate_short
                gain_to_realize = pnl * (
                    trade_value / max(float(h.get("market_value", trade_value)), 1)
                )
                tax_cost = gain_to_realize * rate

            trades.append(
                {
                    "ticker": ticker,
                    "action": action,
                    "current_weight": round(curr_w, 4),
                    "target_weight": round(target_w, 4),
                    "trade_value": round(trade_value, 2),
                    "unrealized_pnl": round(pnl, 2),
                    "tax_cost_if_sold": round(tax_cost, 2),
                    "holding_period": "long-term" if is_long else "short-term",
                    "tax_priority": (
                        "high"
                        if (action == "SELL" and pnl < 0)
                        else (
                            "medium"
                            if (action == "SELL" and pnl >= 0 and is_long)
                            else "low"
                        )
                    ),
                }
            )
            total_tax_cost += tax_cost

        # Sort: sells with losses first (favorable), then buys, then sells with gains last
        priority_order = {"high": 0, "medium": 2, "low": 1}
        trades.sort(
            key=lambda t: (
                (
                    0
                    if (t["action"] == "SELL" and t["unrealized_pnl"] < 0)
                    else 1 if t["action"] == "BUY" else 2
                ),
                priority_order.get(t["tax_priority"], 3),
            )
        )

        return {
            "trades": trades,
            "summary": {
                "total_trades": len(trades),
                "total_trade_value": round(sum(t["trade_value"] for t in trades), 2),
                "estimated_tax_cost": round(total_tax_cost, 2),
                "loss_harvesting_trades": sum(
                    1
                    for t in trades
                    if t["action"] == "SELL" and t["unrealized_pnl"] < 0
                ),
            },
            "recommendation": (
                "Execute sells with losses first to offset gains. "
                "Consider deferring sells with large short-term gains until positions become long-term."
            ),
        }

    @staticmethod
    def compute_after_tax_return(
        pretax_return: float,
        holding_years: float,
        tax_rate_short: float = 0.37,
        tax_rate_long: float = 0.20,
        dividend_yield: float = 0.015,
        turnover_rate: float = 0.10,
    ) -> Dict:
        """
        Estimate after-tax annualized return accounting for capital gains
        distributions and dividend taxes.
        """
        is_long_term = holding_years >= 1.0
        cap_gains_rate = tax_rate_long if is_long_term else tax_rate_short
        dividend_drag = (
            dividend_yield * tax_rate_short
        )  # dividends taxed as ordinary income
        gains_drag = pretax_return * turnover_rate * cap_gains_rate
        after_tax = pretax_return - dividend_drag - gains_drag
        tax_drag = dividend_drag + gains_drag

        return {
            "pretax_return": round(pretax_return, 4),
            "after_tax_return": round(after_tax, 4),
            "total_tax_drag": round(tax_drag, 4),
            "dividend_tax_drag": round(dividend_drag, 4),
            "capital_gains_drag": round(gains_drag, 4),
            "holding_period": "long-term" if is_long_term else "short-term",
            "effective_tax_rate_on_gains": round(cap_gains_rate * 100, 1),
        }
