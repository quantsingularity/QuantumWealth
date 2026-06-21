"""
QuantumWealth AI Engine — Market Predictor
LSTM-style price forecasting (GBM simulation as placeholder for trained model)
and Hidden Markov Model-inspired regime detection.
"""

from __future__ import annotations

import logging
from typing import Dict

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger("ai_engine.market_predictor")


def _fetch_close(ticker: str, period: str = "2y") -> pd.Series:
    data = yf.download(ticker, period=period, progress=False, auto_adjust=True)["Close"]
    if isinstance(data, pd.DataFrame):
        data = data.iloc[:, 0]
    return data.dropna()


class LSTMPredictor:
    """
    Price predictor using Geometric Brownian Motion as a simulation backbone.
    In production: swap GBM for a trained LSTM loaded from disk.
    Adds technical indicators as metadata for UI display.
    """

    def predict(self, ticker: str, horizon_days: int = 30) -> Dict:
        prices = _fetch_close(ticker)
        if len(prices) < 60:
            return {"error": f"Insufficient data for {ticker} (need ≥60 days)."}

        recent = prices.tail(252)
        returns = recent.pct_change().dropna()
        mu = float(returns.mean())
        sigma = float(returns.std())
        last_price = float(recent.iloc[-1])

        # GBM simulation
        rng = np.random.default_rng(42)
        n_paths = 500
        paths = np.zeros((n_paths, horizon_days + 1))
        paths[:, 0] = last_price
        for t in range(1, horizon_days + 1):
            dr = rng.normal(mu, sigma, n_paths)
            paths[:, t] = paths[:, t - 1] * (1 + dr)

        median_path = np.median(paths, axis=0)
        p10_path = np.percentile(paths, 10, axis=0)
        p90_path = np.percentile(paths, 90, axis=0)

        dates = pd.bdate_range(start=pd.Timestamp.today(), periods=horizon_days + 1)
        forecast = [
            {
                "date": str(dates[i].date()),
                "median": round(float(median_path[i]), 4),
                "p10": round(float(p10_path[i]), 4),
                "p90": round(float(p90_path[i]), 4),
            }
            for i in range(len(dates))
        ]

        expected_ret = (median_path[-1] - last_price) / last_price
        direction = (
            "BULLISH"
            if expected_ret > 0.02
            else "BEARISH" if expected_ret < -0.02 else "NEUTRAL"
        )

        # Technical indicators
        sma_20 = float(recent.tail(20).mean())
        sma_50 = float(recent.tail(50).mean())
        rsi = self._compute_rsi(recent)

        return {
            "ticker": ticker,
            "current_price": round(last_price, 4),
            "horizon_days": horizon_days,
            "expected_price": round(float(median_path[-1]), 4),
            "expected_return_pct": round(expected_ret * 100, 2),
            "direction": direction,
            "confidence": "medium",
            "forecast": forecast,
            "technical_indicators": {
                "sma_20": round(sma_20, 4),
                "sma_50": round(sma_50, 4),
                "rsi_14": round(rsi, 2),
                "above_sma_20": last_price > sma_20,
                "above_sma_50": last_price > sma_50,
                "rsi_signal": (
                    "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"
                ),
            },
            "model": "GBM_simulation",
            "note": "Production model uses LSTM trained on 5y OHLCV + technical indicators.",
        }

    @staticmethod
    def _compute_rsi(prices: pd.Series, period: int = 14) -> float:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0.0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty else 50.0


class RegimeDetector:
    """Rolling-statistics regime detection (bull / bear / sideways)."""

    def detect(self, ticker: str) -> Dict:
        prices = _fetch_close(ticker, period="3y")
        returns = prices.pct_change().dropna()

        # FIX: with no (or insufficient) price history, rolling_mean and
        # rolling_vol are empty Series, and .iloc[-1] raises IndexError on
        # an empty Series rather than returning anything usable. Matches
        # the same guard LSTMPredictor.predict() already has.
        if len(returns) < 21:
            return {"error": f"Insufficient data for {ticker} (need >=21 days)."}

        rolling_mean = returns.rolling(21).mean()
        rolling_vol = returns.rolling(21).std()

        last_mean = float(rolling_mean.iloc[-1])
        last_vol = float(rolling_vol.iloc[-1])
        hist_vol = float(rolling_vol.mean())

        if last_mean > 0.0005 and last_vol < hist_vol * 1.2:
            regime = "BULL"
            description = "Positive trend with controlled volatility. Favorable for equity exposure."
            suggested_action = "Maintain or increase equity allocation."
        elif last_mean < -0.0005 or last_vol > hist_vol * 1.5:
            regime = "BEAR"
            description = (
                "Negative trend or elevated volatility. Consider defensive positioning."
            )
            suggested_action = "Reduce risk exposure; consider bonds, gold, or cash."
        else:
            regime = "SIDEWAYS"
            description = "Range-bound consolidation. Reduced directional conviction."
            suggested_action = "Range-trading strategies; collect dividends and wait."

        return {
            "ticker": ticker,
            "regime": regime,
            "description": description,
            "suggested_action": suggested_action,
            "metrics": {
                "rolling_21d_annualized_return_pct": round(last_mean * 252 * 100, 2),
                "rolling_21d_annualized_vol_pct": round(
                    last_vol * np.sqrt(252) * 100, 2
                ),
                "historical_avg_vol_pct": round(hist_vol * np.sqrt(252) * 100, 2),
                "vol_vs_average_ratio": round(
                    last_vol / hist_vol if hist_vol > 0 else 1.0, 2
                ),
            },
        }
