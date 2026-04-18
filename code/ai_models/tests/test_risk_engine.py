"""
Tests for ai_models.risk_engine.engine

Covers:
  - compute_var: historical and parametric methods, confidence scaling, horizon scaling
  - stress_test: known scenario impact, unknown ticker default, all scenarios
  - monte_carlo: output structure, probability bounds, yearly projections
  - full_report: all metrics present, stress tests embedded
  - correlation_matrix: shape, symmetry, diagonal ones, high-correlation detection
"""

import os
import sys
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ai_models.risk_engine.engine import STRESS_SCENARIOS, RiskEngine

from .conftest import RETURNS_4, TICKERS_3, TICKERS_4, WEIGHTS_3, WEIGHTS_4


def _make_mock_fetch(returns_df):
    return patch("ai_models.risk_engine.engine._fetch_returns", return_value=returns_df)


class TestComputeVar:
    def test_historical_var_returns_valid_structure(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.compute_var(TICKERS_4, WEIGHTS_4, 100_000.0)
        assert "var_pct" in result
        assert "var_dollar" in result
        assert "cvar_pct" in result
        assert "cvar_dollar" in result
        assert "method" in result
        assert result["method"] == "historical"

    def test_parametric_var_method(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.compute_var(
                TICKERS_4, WEIGHTS_4, 100_000.0, method="parametric"
            )
        assert result["method"] == "parametric"
        assert "var_dollar" in result

    def test_var_dollar_positive(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.compute_var(TICKERS_4, WEIGHTS_4, 100_000.0)
        assert result["var_dollar"] > 0

    def test_var_scales_with_portfolio_value(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            small = engine.compute_var(TICKERS_4, WEIGHTS_4, 50_000.0)
        with _make_mock_fetch(RETURNS_4):
            large = engine.compute_var(TICKERS_4, WEIGHTS_4, 100_000.0)
        # Double the portfolio value should roughly double the dollar VaR
        assert abs(large["var_dollar"] / max(small["var_dollar"], 1) - 2.0) < 0.1

    def test_higher_confidence_yields_larger_var(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            var90 = engine.compute_var(TICKERS_4, WEIGHTS_4, 100_000.0, confidence=0.90)
        with _make_mock_fetch(RETURNS_4):
            var99 = engine.compute_var(TICKERS_4, WEIGHTS_4, 100_000.0, confidence=0.99)
        assert var99["var_dollar"] >= var90["var_dollar"]

    def test_horizon_scaling_via_sqrt_of_time(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            var1 = engine.compute_var(TICKERS_4, WEIGHTS_4, 100_000.0, horizon_days=1)
        with _make_mock_fetch(RETURNS_4):
            var4 = engine.compute_var(TICKERS_4, WEIGHTS_4, 100_000.0, horizon_days=4)
        # 4-day VaR should be approximately 2x the 1-day VaR (sqrt(4)=2)
        ratio = var4["var_dollar"] / max(var1["var_dollar"], 1e-8)
        assert 1.5 < ratio < 2.5

    def test_cvar_greater_than_or_equal_to_var(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.compute_var(TICKERS_4, WEIGHTS_4, 100_000.0)
        assert result["cvar_dollar"] >= result["var_dollar"] - 0.01

    def test_interpretation_included(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.compute_var(TICKERS_4, WEIGHTS_4, 100_000.0)
        assert "interpretation" in result
        assert isinstance(result["interpretation"], str)
        assert len(result["interpretation"]) > 20


class TestStressTest:
    def test_2008_crisis_produces_large_loss(self):
        engine = RiskEngine()
        result = engine.stress_test(
            ["SPY", "QQQ"], [0.6, 0.4], 100_000.0, "2008_crisis"
        )
        assert result["total_impact_pct"] < -30

    def test_tlt_positive_in_2008_crisis(self):
        """TLT (long bonds) historically gained during the 2008 equity crash."""
        engine = RiskEngine()
        result = engine.stress_test(["TLT"], [1.0], 100_000.0, "2008_crisis")
        # TLT had positive returns in 2008
        assert result["total_impact_dollar"] > 0

    def test_unknown_scenario_returns_error(self):
        engine = RiskEngine()
        result = engine.stress_test(
            TICKERS_3, WEIGHTS_3, 100_000.0, "nonexistent_scenario"
        )
        assert "error" in result

    def test_unknown_ticker_gets_default_shock(self):
        engine = RiskEngine()
        result = engine.stress_test(
            ["UNKNOWN_TICKER_XYZ"], [1.0], 100_000.0, "covid_crash"
        )
        # Default shock is -25%
        assert result["total_impact_pct"] == pytest.approx(-25.0, abs=0.5)

    def test_stressed_value_equals_portfolio_minus_impact(self):
        engine = RiskEngine()
        pv = 100_000.0
        result = engine.stress_test(["SPY"], [1.0], pv, "covid_crash")
        expected = pv + result["total_impact_dollar"]
        assert abs(result["stressed_value"] - expected) < 0.01

    def test_position_impacts_list_has_correct_length(self):
        engine = RiskEngine()
        result = engine.stress_test(TICKERS_3, WEIGHTS_3, 100_000.0, "rate_shock")
        assert len(result["position_impacts"]) == len(TICKERS_3)

    def test_all_stress_scenarios_are_valid(self):
        engine = RiskEngine()
        for scenario in STRESS_SCENARIOS:
            result = engine.stress_test(TICKERS_3, WEIGHTS_3, 100_000.0, scenario)
            assert (
                "total_impact_pct" in result
            ), f"Missing total_impact_pct for {scenario}"
            assert "error" not in result, f"Unexpected error for {scenario}"

    def test_weights_normalized_internally(self):
        """Weights that do not sum to 1 should still produce valid output."""
        engine = RiskEngine()
        # Weights sum to 2 (unnormalized)
        result = engine.stress_test(
            TICKERS_3, [1.2, 0.6, 0.2], 100_000.0, "covid_crash"
        )
        assert "total_impact_pct" in result


class TestMonteCarlo:
    def test_returns_valid_structure(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.monte_carlo(
                TICKERS_4, WEIGHTS_4, 100_000.0, simulations=500
            )
        assert "percentiles" in result
        assert "probability_of_profit" in result
        assert "yearly_projections" in result
        assert "expected_final_value" in result

    def test_percentiles_in_ascending_order(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.monte_carlo(
                TICKERS_4, WEIGHTS_4, 100_000.0, simulations=500
            )
        pct = result["percentiles"]
        assert pct["p5"] <= pct["p25"] <= pct["p50"] <= pct["p75"] <= pct["p95"]

    def test_probability_of_profit_between_0_and_1(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.monte_carlo(
                TICKERS_4, WEIGHTS_4, 100_000.0, simulations=500
            )
        assert 0.0 <= result["probability_of_profit"] <= 1.0

    def test_probability_of_doubling_le_probability_of_profit(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.monte_carlo(
                TICKERS_4, WEIGHTS_4, 100_000.0, simulations=500
            )
        assert result["probability_of_doubling"] <= result["probability_of_profit"]

    def test_yearly_projections_count_matches_horizon(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.monte_carlo(
                TICKERS_4, WEIGHTS_4, 100_000.0, simulations=200, horizon_years=5
            )
        assert len(result["yearly_projections"]) == 5

    def test_yearly_projections_have_required_keys(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.monte_carlo(
                TICKERS_4, WEIGHTS_4, 100_000.0, simulations=200, horizon_years=3
            )
        for yr in result["yearly_projections"]:
            assert "year" in yr
            assert "p10" in yr
            assert "p50" in yr
            assert "p90" in yr

    def test_p10_le_p50_le_p90_for_each_year(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.monte_carlo(
                TICKERS_4, WEIGHTS_4, 100_000.0, simulations=200, horizon_years=5
            )
        for yr in result["yearly_projections"]:
            assert yr["p10"] <= yr["p50"] <= yr["p90"]

    def test_median_value_grows_over_time_for_positive_returns(self):
        """With positive drift, median portfolio value should increase each year."""
        engine = RiskEngine()
        # Use returns with clear positive drift
        high_return = pd.DataFrame(
            np.full((756, 2), 0.001), columns=["A", "B"]  # 25% annual return
        )
        with patch(
            "ai_models.risk_engine.engine._fetch_returns", return_value=high_return
        ):
            result = engine.monte_carlo(
                ["A", "B"], [0.5, 0.5], 100_000.0, simulations=100, horizon_years=5
            )
        medians = [yr["p50"] for yr in result["yearly_projections"]]
        assert medians[-1] > medians[0]


class TestFullReport:
    def test_returns_complete_structure(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.full_report(TICKERS_4, WEIGHTS_4, 100_000.0)
        assert "performance" in result
        assert "risk_metrics" in result
        assert "stress_tests" in result

    def test_performance_metrics_all_present(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.full_report(TICKERS_4, WEIGHTS_4, 100_000.0)
        perf = result["performance"]
        for key in (
            "annualized_return",
            "annualized_volatility",
            "sharpe_ratio",
            "sortino_ratio",
            "calmar_ratio",
            "max_drawdown",
        ):
            assert key in perf, f"Missing performance metric: {key}"

    def test_max_drawdown_is_negative_or_zero(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.full_report(TICKERS_4, WEIGHTS_4, 100_000.0)
        assert result["performance"]["max_drawdown"] <= 0

    def test_volatility_is_positive(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.full_report(TICKERS_4, WEIGHTS_4, 100_000.0)
        assert result["performance"]["annualized_volatility"] > 0

    def test_stress_tests_contains_all_scenarios(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.full_report(TICKERS_4, WEIGHTS_4, 100_000.0)
        for scenario in STRESS_SCENARIOS:
            assert scenario in result["stress_tests"]

    def test_var_metrics_present(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.full_report(TICKERS_4, WEIGHTS_4, 100_000.0)
        risk = result["risk_metrics"]
        for key in ("var_95_pct", "var_95_dollar", "cvar_95_pct", "cvar_95_dollar"):
            assert key in risk


class TestCorrelationMatrix:
    def test_returns_correct_structure(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.correlation_matrix(TICKERS_4)
        assert "tickers" in result
        assert "matrix" in result
        assert "high_correlations" in result

    def test_matrix_is_square(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.correlation_matrix(TICKERS_4)
        matrix = result["matrix"]
        n = len(result["tickers"])
        assert len(matrix) == n
        for row in matrix:
            assert len(row) == n

    def test_diagonal_is_one(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.correlation_matrix(TICKERS_4)
        matrix = np.array(result["matrix"])
        for i in range(len(result["tickers"])):
            assert abs(matrix[i, i] - 1.0) < 0.001

    def test_matrix_is_symmetric(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.correlation_matrix(TICKERS_4)
        matrix = np.array(result["matrix"])
        np.testing.assert_allclose(matrix, matrix.T, atol=1e-6)

    def test_values_between_negative_one_and_one(self):
        engine = RiskEngine()
        with _make_mock_fetch(RETURNS_4):
            result = engine.correlation_matrix(TICKERS_4)
        matrix = np.array(result["matrix"])
        assert matrix.min() >= -1.001
        assert matrix.max() <= 1.001

    def test_high_correlations_threshold_is_080(self):
        engine = RiskEngine()
        # Create highly correlated data
        base = np.random.default_rng(0).normal(0, 1, 756)
        correlated = pd.DataFrame(
            {
                "A": base + np.random.default_rng(1).normal(0, 0.01, 756),
                "B": base + np.random.default_rng(2).normal(0, 0.01, 756),
            }
        )
        with patch(
            "ai_models.risk_engine.engine._fetch_returns", return_value=correlated
        ):
            result = engine.correlation_matrix(["A", "B"])
        # A and B are nearly perfectly correlated, should appear in high_correlations
        assert len(result["high_correlations"]) > 0
        for pair in result["high_correlations"]:
            assert abs(pair["correlation"]) > 0.79
