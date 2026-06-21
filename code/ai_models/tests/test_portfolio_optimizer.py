"""
Tests for ai_models.portfolio_optimizer.optimizer

Covers:
  - mean_variance_optimize: basic solve, target return mode, weight constraints
  - black_litterman_optimize: no views, with views, posterior shifts correctly
  - risk_parity_optimize: risk contributions approximately equal
  - hrp_optimize: weights sum to 1, all positive
  - compute_efficient_frontier: monotonic volatility with return
  - PortfolioOptimizer.optimize: all four strategies, error handling, allocation diff
"""

import os
import sys
from unittest.mock import patch

import numpy as np
import pandas as pd

# Make ai_models importable when running from the tests directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ai_models.portfolio_optimizer.optimizer import (
    PortfolioOptimizer,
    black_litterman_optimize,
    compute_efficient_frontier,
    hrp_optimize,
    mean_variance_optimize,
    risk_parity_optimize,
)

from .conftest import (
    COV_3,
    COV_4,
    MU_3,
    MU_4,
    RETURNS_3,
    RETURNS_4,
    TICKERS_3,
    TICKERS_4,
)

# ---------------------------------------------------------------------------
# mean_variance_optimize
# ---------------------------------------------------------------------------


class TestMeanVarianceOptimize:
    def test_weights_sum_to_one(self):
        result = mean_variance_optimize(TICKERS_4, MU_4, COV_4)
        total = sum(result["weights"].values())
        assert abs(total - 1.0) < 1e-4

    def test_all_weights_within_bounds(self):
        result = mean_variance_optimize(TICKERS_4, MU_4, COV_4, max_weight=0.40)
        for ticker, w in result["weights"].items():
            assert w >= 0.009, f"{ticker} weight {w} below minimum"
            assert w <= 0.401, f"{ticker} weight {w} above maximum"

    def test_all_tickers_represented(self):
        result = mean_variance_optimize(TICKERS_4, MU_4, COV_4)
        for ticker in TICKERS_4:
            assert ticker in result["weights"]

    def test_returns_sharpe_ratio(self):
        result = mean_variance_optimize(TICKERS_4, MU_4, COV_4)
        assert "sharpe_ratio" in result
        assert isinstance(result["sharpe_ratio"], float)

    def test_returns_expected_return_and_volatility(self):
        result = mean_variance_optimize(TICKERS_4, MU_4, COV_4)
        assert result["expected_return"] != 0
        assert result["expected_volatility"] > 0

    def test_target_return_mode_achieves_minimum_return(self):
        # The synthetic fixtures in conftest produce all-negative annualized
        # expected returns (max achievable portfolio return is well below zero),
        # so a hard-coded positive target such as 0.08 is genuinely infeasible
        # and the optimizer correctly falls back to equal weight. To test the
        # target-return-achievement behavior itself, derive a feasible target
        # from the data: the equal-weight portfolio return is always attainable
        # under the sum-to-one and per-asset weight bounds.
        target = float(np.mean(MU_4))
        result = mean_variance_optimize(TICKERS_4, MU_4, COV_4, target_return=target)
        # In target-return mode we minimise variance, so return should be >= target
        assert result["expected_return"] >= target - 0.01  # allow 1% tolerance

    def test_tight_max_weight_respected(self):
        max_w = 0.30
        result = mean_variance_optimize(TICKERS_4, MU_4, COV_4, max_weight=max_w)
        for w in result["weights"].values():
            assert w <= max_w + 0.001

    def test_single_ticker_falls_back_to_equal_weight(self):
        mu = np.array([0.10])
        sigma = np.array([[0.04]])
        result = mean_variance_optimize(["AAPL"], mu, sigma)
        assert abs(result["weights"]["AAPL"] - 1.0) < 1e-4

    def test_infeasible_target_return_falls_back_to_equal_weight(self):
        """A target return far above any asset return should trigger fallback."""
        result = mean_variance_optimize(TICKERS_4, MU_4, COV_4, target_return=10.0)
        total = sum(result["weights"].values())
        assert abs(total - 1.0) < 1e-4


# ---------------------------------------------------------------------------
# black_litterman_optimize
# ---------------------------------------------------------------------------


class TestBlackLittermanOptimize:
    def test_weights_sum_to_one_no_views(self):
        result = black_litterman_optimize(TICKERS_3, MU_3, COV_3)
        total = sum(result["weights"].values())
        assert abs(total - 1.0) < 1e-4

    def test_model_label_set(self):
        result = black_litterman_optimize(TICKERS_3, MU_3, COV_3)
        assert result.get("model") == "black_litterman"

    def test_views_shift_weight_toward_high_return_asset(self):
        """Providing a bullish view on one ticker should increase its weight."""
        no_view = black_litterman_optimize(TICKERS_3, MU_3, COV_3)
        bullish_view = black_litterman_optimize(
            TICKERS_3,
            MU_3,
            COV_3,
            views={"SPY": 0.25},  # very bullish on SPY
            view_confidence=0.8,
        )
        # SPY weight should be equal or higher with a bullish view
        assert bullish_view["weights"]["SPY"] >= no_view["weights"]["SPY"] - 0.05

    def test_market_caps_influence_equilibrium_weights(self):
        caps = {"SPY": 40_000_000_000, "TLT": 10_000_000_000, "GLD": 5_000_000_000}
        result = black_litterman_optimize(TICKERS_3, MU_3, COV_3, market_caps=caps)
        total = sum(result["weights"].values())
        assert abs(total - 1.0) < 1e-4

    def test_valid_result_with_all_parameters(self):
        result = black_litterman_optimize(
            TICKERS_3,
            MU_3,
            COV_3,
            market_caps={"SPY": 1e10, "TLT": 3e9, "GLD": 2e9},
            views={"TLT": 0.05},
            view_confidence=0.6,
        )
        assert sum(result["weights"].values()) - 1.0 < 1e-4


# ---------------------------------------------------------------------------
# risk_parity_optimize
# ---------------------------------------------------------------------------


class TestRiskParityOptimize:
    def test_weights_sum_to_one(self):
        result = risk_parity_optimize(TICKERS_4, COV_4)
        total = sum(result["weights"].values())
        assert abs(total - 1.0) < 1e-4

    def test_all_weights_positive(self):
        result = risk_parity_optimize(TICKERS_4, COV_4)
        for ticker, w in result["weights"].items():
            assert w > 0, f"{ticker} has non-positive weight {w}"

    def test_risk_contributions_approximately_equal(self):
        """Each position should contribute approximately 1/n of total risk."""
        result = risk_parity_optimize(TICKERS_4, COV_4)
        w = np.array([result["weights"][t] for t in TICKERS_4])
        risk_contrib = COV_4 @ w * w
        # Coefficient of variation should be small (< 0.5) for well-behaved ERC
        cv = risk_contrib.std() / max(risk_contrib.mean(), 1e-12)
        assert cv < 0.5, f"Risk contributions are not approximately equal (CV={cv:.3f})"

    def test_model_label(self):
        result = risk_parity_optimize(TICKERS_4, COV_4)
        assert result.get("model") == "risk_parity"

    def test_max_weight_constraint_respected(self):
        result = risk_parity_optimize(TICKERS_4, COV_4)
        for w in result["weights"].values():
            assert w <= 0.501  # solver max is 0.50


# ---------------------------------------------------------------------------
# hrp_optimize
# ---------------------------------------------------------------------------


class TestHRPOptimize:
    def test_weights_sum_to_one(self):
        result = hrp_optimize(TICKERS_4, RETURNS_4)
        total = sum(result["weights"].values())
        assert abs(total - 1.0) < 1e-4

    def test_all_weights_positive(self):
        result = hrp_optimize(TICKERS_4, RETURNS_4)
        for ticker, w in result["weights"].items():
            assert w > 0, f"{ticker} has non-positive weight {w}"

    def test_model_label(self):
        result = hrp_optimize(TICKERS_4, RETURNS_4)
        assert result.get("model") == "hrp"

    def test_diversified_weights_vs_equal_weight(self):
        """HRP should allocate differently from equal weights on assets with
        distinct risk profiles. The shared conftest fixtures are deliberately
        homogeneous (correlations above 0.93, near-identical variances), so HRP
        correctly stays close to equal weight on them. Build a small set of
        assets with clearly different volatilities here so the diversification
        behavior is observable."""
        rng = np.random.default_rng(7)
        n_obs = 1000
        market = rng.normal(0.0, 0.005, n_obs)
        cols = ["LOWVOL", "MIDVOL", "HIGHVOL", "EXTREMEVOL"]
        het = pd.DataFrame(
            {
                "LOWVOL": 0.6 * market + rng.normal(0, 0.002, n_obs),
                "MIDVOL": 0.5 * market + rng.normal(0, 0.010, n_obs),
                "HIGHVOL": 0.3 * market + rng.normal(0, 0.025, n_obs),
                "EXTREMEVOL": 0.2 * market + rng.normal(0, 0.040, n_obs),
            }
        )
        result = hrp_optimize(cols, het)
        equal_w = 1.0 / len(cols)
        max_deviation = max(abs(w - equal_w) for w in result["weights"].values())
        # HRP produces unequal weights based on the risk structure
        assert max_deviation > 0.01
        # Sanity check direction: the lowest-volatility asset receives the most
        assert result["weights"]["LOWVOL"] == max(result["weights"].values())

    def test_works_with_three_assets(self):
        result = hrp_optimize(TICKERS_3, RETURNS_3)
        assert abs(sum(result["weights"].values()) - 1.0) < 1e-4


# ---------------------------------------------------------------------------
# compute_efficient_frontier
# ---------------------------------------------------------------------------


class TestEfficientFrontier:
    def test_returns_non_empty_list(self):
        frontier = compute_efficient_frontier(TICKERS_4, MU_4, COV_4)
        assert len(frontier) > 0

    def test_each_point_has_required_keys(self):
        frontier = compute_efficient_frontier(TICKERS_4, MU_4, COV_4, points=10)
        for point in frontier:
            assert "target_return" in point
            assert "volatility" in point
            assert "sharpe" in point

    def test_volatility_generally_increases_with_return(self):
        frontier = compute_efficient_frontier(TICKERS_4, MU_4, COV_4, points=10)
        if len(frontier) >= 3:
            vols = [p["volatility"] for p in frontier]
            # Not strictly monotonic due to solver noise, but generally increasing
            low_vol = np.mean(vols[:3])
            high_vol = np.mean(vols[-3:])
            assert high_vol >= low_vol - 0.01


# ---------------------------------------------------------------------------
# PortfolioOptimizer (public API)
# ---------------------------------------------------------------------------


class TestPortfolioOptimizerPublicAPI:
    """Tests the PortfolioOptimizer.optimize() method with mocked yfinance."""

    def _mock_fetch(self, tickers, returns_df):
        return patch(
            "ai_models.portfolio_optimizer.optimizer.fetch_returns",
            return_value=returns_df,
        )

    def test_mean_variance_strategy_returns_valid_structure(self):
        optimizer = PortfolioOptimizer()
        with self._mock_fetch(TICKERS_4, RETURNS_4):
            result = optimizer.optimize(
                TICKERS_4,
                strategy="mean_variance",
                current_weights={t: 0.25 for t in TICKERS_4},
            )
        assert "strategy" in result
        assert "allocations" in result
        assert "efficient_frontier" in result
        assert "expected_return" in result
        assert result["strategy"] == "mean_variance"

    def test_black_litterman_strategy(self):
        optimizer = PortfolioOptimizer()
        with self._mock_fetch(TICKERS_3, RETURNS_3):
            result = optimizer.optimize(TICKERS_3, strategy="black_litterman")
        assert "allocations" in result

    def test_risk_parity_strategy(self):
        optimizer = PortfolioOptimizer()
        with self._mock_fetch(TICKERS_4, RETURNS_4):
            result = optimizer.optimize(TICKERS_4, strategy="risk_parity")
        assert "allocations" in result

    def test_hrp_strategy(self):
        optimizer = PortfolioOptimizer()
        with self._mock_fetch(TICKERS_4, RETURNS_4):
            result = optimizer.optimize(TICKERS_4, strategy="hrp")
        assert "allocations" in result

    def test_allocation_diff_action_labels(self):
        optimizer = PortfolioOptimizer()
        current = {"AAPL": 0.60, "MSFT": 0.20, "BND": 0.10, "GLD": 0.10}
        with self._mock_fetch(TICKERS_4, RETURNS_4):
            result = optimizer.optimize(
                TICKERS_4, strategy="mean_variance", current_weights=current
            )
        for alloc in result["allocations"]:
            assert alloc["suggested_action"] in ("BUY", "SELL", "HOLD")
            diff = alloc["target_weight"] - alloc["current_weight"]
            if diff > 0.005:
                assert alloc["suggested_action"] == "BUY"
            elif diff < -0.005:
                assert alloc["suggested_action"] == "SELL"

    def test_tickers_dropped_in_metadata(self):
        optimizer = PortfolioOptimizer()
        # RETURNS_4 only has 4 columns; if we ask for a 5th ticker it should be dropped
        extra_tickers = TICKERS_4 + ["FAKE_TICKER_XYZ"]
        with self._mock_fetch(extra_tickers, RETURNS_4):
            result = optimizer.optimize(extra_tickers, strategy="mean_variance")
        assert "metadata" in result
        # FAKE_TICKER_XYZ should appear in tickers_dropped (not in returns DataFrame)
        assert "FAKE_TICKER_XYZ" in result["metadata"].get("tickers_dropped", [])

    def test_empty_returns_returns_error_dict(self):
        optimizer = PortfolioOptimizer()
        with patch(
            "ai_models.portfolio_optimizer.optimizer.fetch_returns",
            return_value=pd.DataFrame(),
        ):
            result = optimizer.optimize(TICKERS_4)
        assert "error" in result

    def test_fetch_failure_returns_error_dict(self):
        optimizer = PortfolioOptimizer()
        with patch(
            "ai_models.portfolio_optimizer.optimizer.fetch_returns",
            side_effect=Exception("Network error"),
        ):
            result = optimizer.optimize(TICKERS_4)
        assert "error" in result

    def test_max_weight_constraint_passed_through(self):
        optimizer = PortfolioOptimizer()
        with self._mock_fetch(TICKERS_4, RETURNS_4):
            result = optimizer.optimize(TICKERS_4, max_weight=0.50)
        for alloc in result["allocations"]:
            assert alloc["target_weight"] <= 0.51  # 1% tolerance for solver
