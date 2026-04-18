"""
Tests for ai_models.robo_advisor.advisor (plan_goal, compute_rebalance)
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ai_models.robo_advisor.advisor import compute_rebalance, plan_goal

from .conftest import future_datetime

# ---------------------------------------------------------------------------
# plan_goal
# ---------------------------------------------------------------------------


class TestPlanGoal:
    def _base_kwargs(self, **overrides):
        kw = dict(
            goal_type="retirement",
            target_amount=1_000_000.0,
            current_savings=100_000.0,
            monthly_contribution=2_000.0,
            target_date=future_datetime(years=25),
            expected_return=0.07,
            inflation_rate=0.03,
            inflation_adjusted=True,
        )
        kw.update(overrides)
        return kw

    def test_returns_complete_structure(self):
        result = plan_goal(**self._base_kwargs())
        for key in (
            "inflation_adjusted_target",
            "projected_value",
            "probability_of_success",
            "recommended_monthly_contribution",
            "milestones",
            "scenarios",
            "gap_analysis",
            "suggested_portfolio",
        ):
            assert key in result, f"Missing key: {key}"

    def test_probability_of_success_between_0_and_1(self):
        result = plan_goal(**self._base_kwargs())
        assert 0.0 <= result["probability_of_success"] <= 1.0

    def test_long_horizon_produces_high_probability(self):
        """25 years of saving $2000/month toward $1M should be well on track."""
        result = plan_goal(**self._base_kwargs())
        # With 25 years and $2000/month, probability should be high
        assert result["probability_of_success"] > 0.5

    def test_impossible_goal_produces_low_probability(self):
        """$1M goal in 1 year starting from $0 with $100/month is nearly impossible."""
        result = plan_goal(
            goal_type="retirement",
            target_amount=1_000_000.0,
            current_savings=0.0,
            monthly_contribution=100.0,
            target_date=future_datetime(years=1),
            expected_return=0.07,
            inflation_adjusted=False,
        )
        assert result["probability_of_success"] < 0.10

    def test_inflation_adjusted_target_exceeds_nominal_target(self):
        result = plan_goal(**self._base_kwargs())
        assert result["inflation_adjusted_target"] > result["original_target"]

    def test_non_inflation_adjusted_target_equals_nominal(self):
        result = plan_goal(**self._base_kwargs(inflation_adjusted=False))
        assert abs(result["inflation_adjusted_target"] - 1_000_000.0) < 1.0

    def test_milestones_contain_25_50_75_100_percent(self):
        result = plan_goal(**self._base_kwargs())
        milestones = result["milestones"]
        percentages = {m["milestone"] for m in milestones}
        assert "25%" in percentages
        assert "50%" in percentages
        assert "75%" in percentages
        assert "100%" in percentages

    def test_already_achieved_milestones_have_status_achieved(self):
        """With $500K saved toward a $500K goal, 100% milestone should be achieved."""
        result = plan_goal(
            goal_type="custom",
            target_amount=500_000.0,
            current_savings=500_000.0,
            monthly_contribution=0.0,
            target_date=future_datetime(years=5),
            inflation_adjusted=False,
        )
        achieved = [m for m in result["milestones"] if m["status"] == "achieved"]
        assert len(achieved) > 0

    def test_scenarios_contain_conservative_base_optimistic(self):
        result = plan_goal(**self._base_kwargs())
        assert "conservative" in result["scenarios"]
        assert "base" in result["scenarios"]
        assert "optimistic" in result["scenarios"]

    def test_optimistic_scenario_higher_than_conservative(self):
        result = plan_goal(**self._base_kwargs())
        opt_prob = result["scenarios"]["optimistic"]["probability_of_success"]
        con_prob = result["scenarios"]["conservative"]["probability_of_success"]
        assert opt_prob >= con_prob

    def test_suggested_portfolio_provided_for_known_goal_types(self):
        for goal_type in ("retirement", "education", "house", "emergency_fund"):
            result = plan_goal(
                goal_type=goal_type,
                target_amount=100_000.0,
                current_savings=10_000.0,
                monthly_contribution=500.0,
                target_date=future_datetime(years=10),
                inflation_adjusted=False,
            )
            assert result["suggested_portfolio"] is not None
            assert sum(result["suggested_portfolio"].values()) == pytest.approx(
                1.0, abs=0.01
            )

    def test_required_contribution_higher_than_current_when_on_track(self):
        """If monthly contribution is far below what is needed, gap should be positive."""
        result = plan_goal(
            goal_type="custom",
            target_amount=10_000_000.0,
            current_savings=0.0,
            monthly_contribution=100.0,
            target_date=future_datetime(years=10),
            inflation_adjusted=False,
        )
        assert result["recommended_monthly_contribution"] > 100.0
        assert result["contribution_gap"] > 0

    def test_gap_analysis_on_track_flag(self):
        result = plan_goal(**self._base_kwargs())
        assert "on_track" in result["gap_analysis"]
        assert isinstance(result["gap_analysis"]["on_track"], bool)


# ---------------------------------------------------------------------------
# compute_rebalance
# ---------------------------------------------------------------------------


class TestComputeRebalance:
    def _holdings(self, weights: dict):
        return [
            {
                "ticker": t,
                "current_weight": w,
                "market_value": w * 100_000,
                "average_cost": 100.0,
                "current_price": 110.0,
            }
            for t, w in weights.items()
        ]

    def test_no_drift_no_trades(self):
        holdings = self._holdings({"AAPL": 0.60, "BND": 0.40})
        target = {"AAPL": 0.60, "BND": 0.40}
        result = compute_rebalance(holdings, target, 100_000.0, drift_threshold=0.05)
        assert not result["needs_rebalancing"]
        assert len(result["trades"]) == 0

    def test_large_drift_triggers_rebalancing(self):
        holdings = self._holdings({"AAPL": 0.90, "BND": 0.10})
        target = {"AAPL": 0.50, "BND": 0.50}
        result = compute_rebalance(holdings, target, 100_000.0, drift_threshold=0.05)
        assert result["needs_rebalancing"]
        assert len(result["trades"]) >= 1

    def test_sell_comes_before_buy_in_trade_list(self):
        holdings = self._holdings({"AAPL": 0.90, "BND": 0.10})
        target = {"AAPL": 0.50, "BND": 0.50}
        result = compute_rebalance(holdings, target, 100_000.0, drift_threshold=0.01)
        trades = result["trades"]
        sell_indices = [i for i, t in enumerate(trades) if t["action"] == "SELL"]
        buy_indices = [i for i, t in enumerate(trades) if t["action"] == "BUY"]
        if sell_indices and buy_indices:
            assert max(sell_indices) < min(buy_indices)

    def test_min_trade_value_filters_small_trades(self):
        holdings = self._holdings({"AAPL": 0.51, "BND": 0.49})
        target = {"AAPL": 0.50, "BND": 0.50}
        result = compute_rebalance(
            holdings, target, 100_000.0, drift_threshold=0.005, min_trade_value=500.0
        )
        # Trade value is 1% of 100k = $1000 for AAPL, should pass the $500 filter
        # But with a $2000 min, it should be filtered out
        result_filtered = compute_rebalance(
            holdings, target, 100_000.0, drift_threshold=0.005, min_trade_value=2000.0
        )
        assert len(result_filtered["trades"]) <= len(result["trades"])

    def test_total_drift_is_sum_of_per_position_drifts(self):
        holdings = self._holdings({"AAPL": 0.70, "BND": 0.30})
        target = {"AAPL": 0.50, "BND": 0.50}
        result = compute_rebalance(holdings, target, 100_000.0, drift_threshold=0.01)
        expected_drift = abs(0.70 - 0.50) + abs(0.30 - 0.50)
        assert abs(result["total_drift"] - expected_drift) < 0.001

    def test_trade_count_field_matches_trades_list(self):
        holdings = self._holdings({"AAPL": 0.90, "BND": 0.10})
        target = {"AAPL": 0.50, "BND": 0.50}
        result = compute_rebalance(holdings, target, 100_000.0, drift_threshold=0.01)
        assert result["trade_count"] == len(result["trades"])

    def test_estimated_commission_is_small_fraction(self):
        holdings = self._holdings({"AAPL": 0.90, "BND": 0.10})
        target = {"AAPL": 0.50, "BND": 0.50}
        result = compute_rebalance(holdings, target, 100_000.0, drift_threshold=0.01)
        # Commission is 5bps = 0.05% of total trade value
        expected_max = result["total_trade_value"] * 0.001
        assert result["estimated_commission"] <= expected_max + 0.01

    def test_missing_target_ticker_keeps_current_weight(self):
        holdings = self._holdings({"AAPL": 0.60, "BND": 0.40})
        # BND not in target; rebalance should not produce a BND trade
        target = {"AAPL": 0.60}
        result = compute_rebalance(holdings, target, 100_000.0, drift_threshold=0.05)
        bnd_trades = [t for t in result["trades"] if t["ticker"] == "BND"]
        assert len(bnd_trades) == 0
