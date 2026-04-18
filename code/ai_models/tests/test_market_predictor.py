"""
Tests for ai_models.market_predictor.predictor

Covers:
  - LSTMPredictor.predict: structure, direction labels, forecast length, technical indicators
  - RegimeDetector.detect: structure, valid regime labels, metric types
"""

import os
import sys
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ai_models.market_predictor.predictor import LSTMPredictor, RegimeDetector


def _make_price_series(n: int = 300, trend: float = 0.0003) -> pd.Series:
    """Generate a synthetic price series."""
    rng = np.random.default_rng(42)
    returns = rng.normal(trend, 0.012, n)
    prices = 100.0 * np.cumprod(1 + returns)
    return pd.Series(prices, name="Close")


def _patch_close(series: pd.Series):
    return patch(
        "ai_models.market_predictor.predictor._fetch_close", return_value=series
    )


class TestLSTMPredictor:
    def test_returns_valid_structure(self):
        predictor = LSTMPredictor()
        with _patch_close(_make_price_series(300)):
            result = predictor.predict("AAPL", horizon_days=30)
        assert "ticker" in result
        assert "current_price" in result
        assert "expected_price" in result
        assert "expected_return_pct" in result
        assert "direction" in result
        assert "forecast" in result
        assert "technical_indicators" in result

    def test_forecast_length_matches_horizon(self):
        predictor = LSTMPredictor()
        with _patch_close(_make_price_series(300)):
            result = predictor.predict("AAPL", horizon_days=20)
        # Forecast includes day 0 (current) through day horizon
        assert len(result["forecast"]) == 21  # horizon + 1

    def test_forecast_entries_have_required_keys(self):
        predictor = LSTMPredictor()
        with _patch_close(_make_price_series(300)):
            result = predictor.predict("AAPL", horizon_days=5)
        for entry in result["forecast"]:
            assert "date" in entry
            assert "median" in entry
            assert "p10" in entry
            assert "p90" in entry

    def test_p10_le_median_le_p90_in_forecast(self):
        predictor = LSTMPredictor()
        with _patch_close(_make_price_series(300)):
            result = predictor.predict("AAPL", horizon_days=10)
        for entry in result["forecast"]:
            assert entry["p10"] <= entry["median"], f"p10 > median on {entry['date']}"
            assert entry["median"] <= entry["p90"], f"median > p90 on {entry['date']}"

    def test_direction_label_is_valid(self):
        predictor = LSTMPredictor()
        with _patch_close(_make_price_series(300)):
            result = predictor.predict("AAPL", horizon_days=30)
        assert result["direction"] in ("BULLISH", "BEARISH", "NEUTRAL")

    def test_bullish_direction_for_strong_uptrend(self):
        """A strongly upward-trending price series should produce a BULLISH signal."""
        predictor = LSTMPredictor()
        uptrend = _make_price_series(300, trend=0.003)  # very high daily return
        with _patch_close(uptrend):
            result = predictor.predict("UPTREND", horizon_days=30)
        assert result["direction"] == "BULLISH"

    def test_bearish_direction_for_strong_downtrend(self):
        predictor = LSTMPredictor()
        downtrend = _make_price_series(300, trend=-0.003)
        with _patch_close(downtrend):
            result = predictor.predict("DOWN", horizon_days=30)
        assert result["direction"] == "BEARISH"

    def test_insufficient_data_returns_error(self):
        predictor = LSTMPredictor()
        short_series = _make_price_series(n=20)  # too short
        with _patch_close(short_series):
            result = predictor.predict("SHORT", horizon_days=30)
        assert "error" in result

    def test_technical_indicators_include_sma_and_rsi(self):
        predictor = LSTMPredictor()
        with _patch_close(_make_price_series(300)):
            result = predictor.predict("AAPL", horizon_days=30)
        indicators = result["technical_indicators"]
        assert "sma_20" in indicators
        assert "sma_50" in indicators
        assert "rsi_14" in indicators

    def test_rsi_in_valid_range(self):
        predictor = LSTMPredictor()
        with _patch_close(_make_price_series(300)):
            result = predictor.predict("AAPL", horizon_days=30)
        rsi = result["technical_indicators"]["rsi_14"]
        assert 0.0 <= rsi <= 100.0

    def test_current_price_matches_last_price_in_series(self):
        predictor = LSTMPredictor()
        prices = _make_price_series(300)
        with _patch_close(prices):
            result = predictor.predict("AAPL", horizon_days=5)
        assert abs(result["current_price"] - float(prices.tail(252).iloc[-1])) < 0.01

    def test_model_field_present(self):
        predictor = LSTMPredictor()
        with _patch_close(_make_price_series(300)):
            result = predictor.predict("AAPL", horizon_days=5)
        assert "model" in result


class TestRegimeDetector:
    def test_returns_valid_structure(self):
        detector = RegimeDetector()
        with _patch_close(_make_price_series(400)):
            result = detector.detect("SPY")
        assert "ticker" in result
        assert "regime" in result
        assert "description" in result
        assert "metrics" in result
        assert "suggested_action" in result

    def test_regime_is_valid_label(self):
        detector = RegimeDetector()
        with _patch_close(_make_price_series(400)):
            result = detector.detect("SPY")
        assert result["regime"] in ("BULL", "BEAR", "SIDEWAYS")

    def test_bull_regime_for_strong_uptrend(self):
        detector = RegimeDetector()
        # Strong uptrend with low volatility
        rng = np.random.default_rng(1)
        bull_returns = pd.Series(rng.normal(0.002, 0.005, 756))
        bull_prices = 100.0 * (1 + bull_returns).cumprod()
        with _patch_close(bull_prices):
            result = detector.detect("BULL_ASSET")
        assert result["regime"] == "BULL"

    def test_bear_regime_for_high_volatility(self):
        detector = RegimeDetector()
        rng = np.random.default_rng(2)
        # Very high volatility with negative trend
        bear_returns = pd.Series(rng.normal(-0.003, 0.05, 756))
        bear_prices = 100.0 * (1 + bear_returns).cumprod()
        with _patch_close(bear_prices):
            result = detector.detect("BEAR_ASSET")
        assert result["regime"] == "BEAR"

    def test_metrics_contain_numeric_values(self):
        detector = RegimeDetector()
        with _patch_close(_make_price_series(400)):
            result = detector.detect("SPY")
        metrics = result["metrics"]
        for key, val in metrics.items():
            assert isinstance(val, (int, float)), f"{key} is not numeric: {val}"

    def test_rolling_return_is_annualized_percentage(self):
        detector = RegimeDetector()
        with _patch_close(_make_price_series(400)):
            result = detector.detect("SPY")
        # Rolling return is expressed as annualized %, so range should be plausible
        ann_ret = result["metrics"]["rolling_21d_annualized_return_pct"]
        assert -200 <= ann_ret <= 200

    def test_vol_ratio_positive(self):
        detector = RegimeDetector()
        with _patch_close(_make_price_series(400)):
            result = detector.detect("SPY")
        assert result["metrics"]["vol_vs_average_ratio"] > 0
