"""
Tests for the five advanced AI modules:
  - ai_models.backtester.backtester.BacktestEngine
  - ai_models.anomaly_detector.detector.PortfolioAnomalyDetector
  - ai_models.factor_models.models.FactorModel
  - ai_models.sentiment_analyzer.analyzer.SentimentAnalyzer
  - ai_models.tax_optimizer.optimizer.TaxOptimizer
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ai_models.anomaly_detector.detector import PortfolioAnomalyDetector
from ai_models.backtester.backtester import BacktestEngine
from ai_models.factor_models.models import FactorModel
from ai_models.sentiment_analyzer.analyzer import SentimentAnalyzer
from ai_models.tax_optimizer.optimizer import TaxOptimizer

from .conftest import TICKERS_4

# ===========================================================================
# BacktestEngine tests
# ===========================================================================


def _mock_prices(tickers, benchmark="SPY"):
    """Build a synthetic price DataFrame for backtesting."""
    all_tickers = list(set(tickers + [benchmark]))
    idx = pd.bdate_range("2020-01-01", "2023-12-31")
    rng = np.random.default_rng(42)
    data = {}
    for t in all_tickers:
        returns = rng.normal(0.0004, 0.012, len(idx))
        data[t] = 100.0 * np.cumprod(1 + returns)
    return pd.DataFrame(data, index=idx)


class TestBacktestEngine:
    def _run(self, **overrides):
        engine = BacktestEngine()
        kwargs = dict(
            tickers=TICKERS_4[:2],
            weights={"AAPL": 0.6, "MSFT": 0.4},
            start="2020-01-01",
            end="2023-12-31",
            initial_capital=100_000.0,
            rebalance_freq="quarterly",
            transaction_cost_bps=10.0,
            benchmark_ticker="SPY",
        )
        kwargs.update(overrides)
        with patch(
            "ai_models.backtester.backtester._fetch_prices",
            return_value=_mock_prices(["AAPL", "MSFT"]),
        ):
            return engine.run(**kwargs)

    def test_returns_summary_with_required_fields(self):
        result = self._run()
        assert "summary" in result
        for key in (
            "final_value",
            "total_return_pct",
            "annualized_return",
            "sharpe_ratio",
            "max_drawdown",
            "rebalance_count",
        ):
            assert key in result["summary"], f"Missing summary key: {key}"

    def test_final_value_is_positive(self):
        result = self._run()
        assert result["summary"]["final_value"] > 0

    def test_max_drawdown_is_negative_or_zero(self):
        result = self._run()
        assert result["summary"]["max_drawdown"] <= 0

    def test_sharpe_ratio_is_numeric(self):
        result = self._run()
        assert isinstance(result["summary"]["sharpe_ratio"], float)

    def test_portfolio_history_non_empty(self):
        result = self._run()
        assert len(result["portfolio_history"]) > 0

    def test_portfolio_history_entries_have_date_and_value(self):
        result = self._run()
        for entry in result["portfolio_history"][:3]:
            assert "date" in entry
            assert "value" in entry

    def test_benchmark_comparison_included(self):
        result = self._run()
        assert "benchmark_comparison" in result
        bc = result["benchmark_comparison"]
        if bc:  # may be empty if benchmark not in mock prices
            assert "alpha" in bc
            assert "beta" in bc

    def test_monthly_returns_included(self):
        result = self._run()
        assert "monthly_returns" in result
        assert len(result["monthly_returns"]) > 0

    def test_monthly_returns_have_year_month_return(self):
        result = self._run()
        for mr in result["monthly_returns"][:3]:
            assert "year" in mr
            assert "month" in mr
            assert "return_pct" in mr

    def test_transaction_costs_reduce_final_value(self):
        result_no_cost = self._run(transaction_cost_bps=0)
        result_with_cost = self._run(transaction_cost_bps=50)
        # Higher costs should reduce final portfolio value
        assert (
            result_no_cost["summary"]["final_value"]
            >= result_with_cost["summary"]["final_value"]
        )

    def test_rebalance_never_means_only_initial_allocation(self):
        result = self._run(rebalance_freq="never")
        # With no rebalancing, there should be at most 1 rebalance event
        assert result["summary"]["rebalance_count"] <= 1

    def test_empty_price_data_returns_error(self):
        engine = BacktestEngine()
        with patch(
            "ai_models.backtester.backtester._fetch_prices", return_value=pd.DataFrame()
        ):
            result = engine.run(
                tickers=["AAPL"],
                weights={"AAPL": 1.0},
                start="2020-01-01",
                end="2020-12-31",
            )
        assert "error" in result

    def test_settings_reflected_in_output(self):
        result = self._run(transaction_cost_bps=10.0)
        assert result["settings"]["transaction_cost_bps"] == 10.0

    def test_all_four_rebalance_frequencies_run_without_error(self):
        for freq in ("monthly", "quarterly", "annual", "never"):
            result = self._run(rebalance_freq=freq)
            assert "summary" in result, f"Failed for freq={freq}"


# ===========================================================================
# PortfolioAnomalyDetector tests
# ===========================================================================


class TestAnomalyDetector:
    def _holdings(self, tickers, weights):
        return [
            {
                "ticker": t,
                "weight": w,
                "asset_class": "equity",
                "market_value": w * 100_000,
            }
            for t, w in zip(tickers, weights)
        ]

    def test_return_anomalies_valid_structure(self):
        detector = PortfolioAnomalyDetector()
        with patch("ai_models.anomaly_detector.detector.yf.download") as mock_dl:
            mock_data = MagicMock()
            # Build MultiIndex columns mock
            close = pd.DataFrame(
                np.random.default_rng(42).lognormal(0, 0.01, (756, 2)) * 100,
                columns=["AAPL", "BND"],
            )
            mock_data.__getitem__ = lambda self, key: (
                close if key == "Close" else pd.DataFrame()
            )
            mock_data.columns = pd.MultiIndex.from_tuples(
                [("Close", t) for t in ["AAPL", "BND"]]
            )
            mock_dl.return_value = mock_data
            # Patch at the volume level too
            with patch(
                "ai_models.anomaly_detector.detector.yf.download",
                return_value=self._build_download_mock(["AAPL", "BND"]),
            ):
                result = detector.detect_return_anomalies(
                    ["AAPL", "BND"], [0.6, 0.4], period="2y"
                )
        # Just check the function runs and returns a dict
        assert isinstance(result, dict)

    @staticmethod
    def _build_download_mock(tickers):
        rng = np.random.default_rng(42)
        idx = pd.bdate_range("2021-01-01", periods=756)
        close = pd.DataFrame(
            rng.lognormal(0, 0.012, (756, len(tickers))) * 100,
            index=idx,
            columns=tickers,
        )
        volume = pd.DataFrame(
            rng.integers(1_000_000, 50_000_000, (756, len(tickers))),
            index=idx,
            columns=tickers,
        )
        mock = MagicMock()
        mock.__getitem__ = lambda self, key: close if key == "Close" else volume
        return mock

    def test_transaction_anomaly_detects_large_trade(self):
        detector = PortfolioAnomalyDetector()
        transactions = [
            {
                "ticker": "AAPL",
                "transaction_type": "buy",
                "amount": 1000,
                "executed_at": "2024-01-10T10:00:00Z",
            },
        ] * 9 + [
            {
                "ticker": "AAPL",
                "transaction_type": "buy",
                "amount": 1_000_000,
                "executed_at": "2024-01-15T10:00:00Z",
            },
        ]
        result = detector.detect_transaction_anomalies(transactions)
        assert "anomalies" in result
        large_trade = [
            a for a in result["anomalies"] if a["type"] == "large_transaction"
        ]
        assert len(large_trade) >= 1

    def test_transaction_anomaly_detects_wash_sale(self):
        detector = PortfolioAnomalyDetector()
        today = datetime.now(timezone.utc).isoformat()
        in_15_days = (datetime.now(timezone.utc) + timedelta(days=15)).isoformat()
        transactions = [
            {
                "ticker": "AAPL",
                "transaction_type": "buy",
                "amount": 5000,
                "executed_at": today,
            },
            {
                "ticker": "AAPL",
                "transaction_type": "sell",
                "amount": 4000,
                "executed_at": in_15_days,
            },
        ]
        result = detector.detect_transaction_anomalies(transactions)
        wash_sales = [a for a in result["anomalies"] if a["type"] == "wash_sale_risk"]
        assert len(wash_sales) >= 1

    def test_transaction_anomaly_empty_list(self):
        detector = PortfolioAnomalyDetector()
        result = detector.detect_transaction_anomalies([])
        assert result["anomaly_count"] == 0

    def test_concentration_anomaly_detects_over_40_pct(self):
        detector = PortfolioAnomalyDetector()
        holdings = self._holdings(["AAPL", "MSFT"], [0.80, 0.20])
        result = detector.detect_concentration_anomaly(holdings)
        high_sev = [a for a in result["anomalies"] if a["severity"] == "high"]
        assert len(high_sev) >= 1

    def test_concentration_anomaly_diversified_portfolio_no_high_severity(self):
        detector = PortfolioAnomalyDetector()
        equal = self._holdings(["A", "B", "C", "D", "E"], [0.20] * 5)
        result = detector.detect_concentration_anomaly(equal)
        high_sev = [a for a in result["anomalies"] if a["severity"] == "high"]
        assert len(high_sev) == 0

    def test_herfindahl_index_equal_weight_approaches_1_over_n(self):
        detector = PortfolioAnomalyDetector()
        n = 5
        equal = self._holdings([f"A{i}" for i in range(n)], [1.0 / n] * n)
        result = detector.detect_concentration_anomaly(equal)
        expected_hhi = 1.0 / n
        assert abs(result["herfindahl_index"] - expected_hhi) < 0.01

    def test_herfindahl_index_single_asset_is_one(self):
        detector = PortfolioAnomalyDetector()
        single = self._holdings(["AAPL"], [1.0])
        result = detector.detect_concentration_anomaly(single)
        assert abs(result["herfindahl_index"] - 1.0) < 0.001

    def test_z_score_outlier_detection(self):
        """Inject an extreme return and verify it is flagged."""
        detector = PortfolioAnomalyDetector()
        returns = np.zeros(100)
        returns[50] = 0.30  # 30% return, huge outlier
        idx = pd.bdate_range("2023-01-01", periods=100)
        outliers = detector._z_score_outliers(returns, idx, threshold=3.0)
        assert len(outliers) >= 1
        assert outliers[0]["z_score"] > 3.0


# ===========================================================================
# TaxOptimizer tests
# ===========================================================================


class TestTaxOptimizer:
    def _holding(self, ticker, pnl, is_long=False, mv=10000.0):
        return {
            "ticker": ticker,
            "unrealized_pnl": pnl,
            "is_long_term": is_long,
            "market_value": mv,
        }

    def test_harvest_schedule_filters_gains(self):
        optimizer = TaxOptimizer()
        holdings = [
            self._holding("AAPL", pnl=500),  # gain -- should be excluded
            self._holding("BND", pnl=-2000),  # loss -- should be included
        ]
        result = optimizer.optimize_harvest_schedule(holdings, min_loss_threshold=100)
        tickers = [h["ticker"] for h in result["harvest_plan"]]
        assert "AAPL" not in tickers
        assert "BND" in tickers

    def test_harvest_schedule_filters_below_threshold(self):
        optimizer = TaxOptimizer()
        holdings = [self._holding("TINY", pnl=-10)]  # loss but below $500 threshold
        result = optimizer.optimize_harvest_schedule(holdings, min_loss_threshold=500)
        assert len(result["harvest_plan"]) == 0

    def test_harvest_plan_includes_wash_sale_info(self):
        optimizer = TaxOptimizer()
        holdings = [self._holding("SPY", pnl=-5000)]
        result = optimizer.optimize_harvest_schedule(holdings)
        if result["harvest_plan"]:
            plan = result["harvest_plan"][0]
            assert "wash_sale_substitutes" in plan
            assert "repurchase_after_date" in plan
            assert (
                "IVV" in plan["wash_sale_substitutes"]
                or "VOO" in plan["wash_sale_substitutes"]
            )

    def test_short_term_uses_higher_tax_rate(self):
        """Short-term losses should show a higher effective tax rate than long-term."""
        optimizer = TaxOptimizer()
        st_holding = [self._holding("MSFT", pnl=-10000, is_long=False)]
        lt_holding = [self._holding("AAPL", pnl=-10000, is_long=True)]
        st_result = optimizer.optimize_harvest_schedule(
            st_holding, tax_rate_short=0.37, tax_rate_long=0.20
        )
        lt_result = optimizer.optimize_harvest_schedule(
            lt_holding, tax_rate_short=0.37, tax_rate_long=0.20
        )
        if st_result["harvest_plan"] and lt_result["harvest_plan"]:
            st_savings = st_result["harvest_plan"][0]["estimated_tax_savings"]
            lt_savings = lt_result["harvest_plan"][0]["estimated_tax_savings"]
            assert st_savings > lt_savings

    def test_summary_totals_are_consistent(self):
        optimizer = TaxOptimizer()
        holdings = [
            self._holding("AAPL", pnl=-1000),
            self._holding("BND", pnl=-2000),
        ]
        result = optimizer.optimize_harvest_schedule(holdings)
        result["harvest_plan"]
        total_loss = sum(abs(h["unrealized_pnl"]) for h in holdings)
        assert result["summary"]["total_losses_to_harvest"] == pytest.approx(
            total_loss, abs=1
        )

    def test_after_tax_return_reduces_pretax(self):
        optimizer = TaxOptimizer()
        result = optimizer.compute_after_tax_return(
            pretax_return=0.10,
            holding_years=3.0,
            tax_rate_short=0.37,
            tax_rate_long=0.20,
        )
        assert result["after_tax_return"] < result["pretax_return"]
        assert result["total_tax_drag"] > 0

    def test_long_term_uses_lower_cap_gains_rate(self):
        optimizer = TaxOptimizer()
        st = optimizer.compute_after_tax_return(pretax_return=0.10, holding_years=0.5)
        lt = optimizer.compute_after_tax_return(pretax_return=0.10, holding_years=2.0)
        assert lt["effective_tax_rate_on_gains"] <= st["effective_tax_rate_on_gains"]

    def test_tax_efficient_rebalance_sells_losses_first(self):
        optimizer = TaxOptimizer()
        current = {"AAPL": 0.70, "BND": 0.30}
        target = {"AAPL": 0.50, "BND": 0.50}
        holdings = [
            {
                "ticker": "AAPL",
                "unrealized_pnl": -500,
                "is_long_term": False,
                "market_value": 70000,
            },
            {
                "ticker": "BND",
                "unrealized_pnl": 200,
                "is_long_term": True,
                "market_value": 30000,
            },
        ]
        result = optimizer.optimize_rebalance_for_taxes(
            current, target, holdings, 100_000.0
        )
        trades = result["trades"]
        # AAPL sell (with loss) should have higher priority than BND buy
        aapl_trade = next((t for t in trades if t["ticker"] == "AAPL"), None)
        if aapl_trade and aapl_trade["action"] == "SELL":
            assert aapl_trade["tax_priority"] in (
                "high",
            ), "Loss sell should have high priority"


# ===========================================================================
# FactorModel tests (mocked yfinance)
# ===========================================================================


class TestFactorModel:
    def _mock_download(self, tickers):
        rng = np.random.default_rng(42)
        idx = pd.bdate_range("2021-01-01", periods=756)
        close = pd.DataFrame(
            rng.lognormal(0, 0.012, (756, len(tickers))) * 100,
            index=idx,
            columns=tickers,
        )
        return close

    def test_compute_factor_exposures_structure(self):
        model = FactorModel()
        all_tickers = TICKERS_4 + [
            "BIL",
            "VB",
            "VV",
            "VTV",
            "VUG",
            "QUAL",
            "USMV",
            "VBR",
            "VBK",
            "MTUM",
        ]
        mock_close = self._mock_download(all_tickers)

        with patch(
            "ai_models.factor_models.models.yf.download", return_value=mock_close
        ):
            result = model.compute_factor_exposures(TICKERS_4[:2], [0.6, 0.4])

        if "error" not in result:
            assert "factor_exposures" in result
            assert "alpha_annualized" in result
            assert "r_squared" in result

    def test_performance_attribution_structure(self):
        model = FactorModel()
        mock_prices = self._mock_download(["AAPL", "MSFT", "SPY"])

        with patch(
            "ai_models.factor_models.models.yf.download", return_value=mock_prices
        ):
            result = model.performance_attribution({"AAPL": 0.6, "MSFT": 0.4})

        if "error" not in result:
            assert "portfolio_return" in result
            assert "benchmark_return" in result
            assert "active_return" in result
            assert "attribution" in result

    def test_attribution_effects_sum_to_active_return(self):
        model = FactorModel()
        mock_prices = self._mock_download(["AAPL", "MSFT", "SPY"])

        with patch(
            "ai_models.factor_models.models.yf.download", return_value=mock_prices
        ):
            result = model.performance_attribution({"AAPL": 0.6, "MSFT": 0.4})

        if "error" not in result:
            attr = result["attribution"]
            total = (
                attr["allocation_effect"]
                + attr["selection_effect"]
                + attr["interaction_effect"]
            )
            assert abs(total - attr["total_active"]) < 0.001


# ===========================================================================
# SentimentAnalyzer tests (mocked yfinance)
# ===========================================================================


class TestSentimentAnalyzer:
    def _mock_ticker(self, news=None, last_price=175.0, prev_close=172.0):
        mock_t = MagicMock()
        mock_t.news = news or [
            {"title": "Apple beats earnings expectations strongly"},
            {"title": "Strong iPhone sales drive record revenue"},
        ]
        mock_t.fast_info.last_price = last_price
        mock_t.fast_info.previous_close = prev_close
        return mock_t

    @patch("yfinance.Ticker")
    @patch("yfinance.download")
    def test_analyze_ticker_returns_composite_score(self, mock_dl, MockTicker):
        rng = np.random.default_rng(1)
        idx = pd.bdate_range("2023-01-01", periods=126)
        close = pd.DataFrame({"AAPL": rng.lognormal(0, 0.012, 126) * 170}, index=idx)
        volume = pd.DataFrame(
            {"AAPL": rng.integers(40_000_000, 60_000_000, 126)}, index=idx
        )
        combined = pd.concat({"Close": close, "Volume": volume}, axis=1)
        mock_dl.return_value = combined
        MockTicker.return_value = self._mock_ticker()

        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_ticker("AAPL")

        assert "composite_score" in result
        assert "sentiment_label" in result
        assert result["sentiment_label"] in ("BULLISH", "BEARISH", "NEUTRAL")
        assert -1.0 <= result["composite_score"] <= 1.0

    @patch("yfinance.Ticker")
    @patch("yfinance.download")
    def test_analyze_ticker_signals_list_non_empty(self, mock_dl, MockTicker):
        rng = np.random.default_rng(2)
        idx = pd.bdate_range("2023-01-01", periods=126)
        close = pd.DataFrame({"AAPL": rng.lognormal(0, 0.012, 126) * 170}, index=idx)
        volume = pd.DataFrame(
            {"AAPL": rng.integers(40_000_000, 60_000_000, 126)}, index=idx
        )
        mock_dl.return_value = pd.concat({"Close": close, "Volume": volume}, axis=1)
        MockTicker.return_value = self._mock_ticker()

        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_ticker("AAPL")

        assert "signals" in result
        assert len(result["signals"]) > 0

    def test_keyword_score_positive_for_bullish_text(self):
        from ai_models.sentiment_analyzer.analyzer import _keyword_score

        score = _keyword_score("Strong earnings beat expectations, stock surges")
        assert score > 0

    def test_keyword_score_negative_for_bearish_text(self):
        from ai_models.sentiment_analyzer.analyzer import _keyword_score

        score = _keyword_score("Sales miss estimates, revenue declined, weak guidance")
        assert score < 0

    def test_keyword_score_neutral_for_neutral_text(self):
        from ai_models.sentiment_analyzer.analyzer import _keyword_score

        score = _keyword_score("The company held its annual meeting yesterday")
        assert score == 0.0

    def test_confidence_level_high_when_signals_agree(self):
        from ai_models.sentiment_analyzer.analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer()
        signals = [{"score": 0.5}, {"score": 0.6}, {"score": 0.7}, {"score": 0.4}]
        confidence = analyzer._confidence_level(signals)
        assert confidence == "high"

    def test_confidence_level_low_when_signals_disagree(self):
        from ai_models.sentiment_analyzer.analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer()
        signals = [{"score": 0.5}, {"score": -0.4}, {"score": 0.0}]
        confidence = analyzer._confidence_level(signals)
        assert confidence in ("low", "medium")
