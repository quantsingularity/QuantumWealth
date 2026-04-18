"""
QuantumWealth AI Models -- Sentiment Analyzer
=============================================
Analyzes market sentiment from:
  - Yahoo Finance news headlines (via yfinance)
  - Price momentum signals
  - Volume-price divergence signals
  - Social sentiment proxies (put-call ratio via ETF flows)

Uses VADER (Valence Aware Dictionary and sEntiment Reasoner) for
lexicon-based sentiment scoring -- no GPU or external API required.

Install: pip install vaderSentiment
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Dict, List

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger("ai_models.sentiment_analyzer")


def _vader_score(text: str) -> float:
    """Return compound VADER score in [-1, +1]. Fallback to 0 if not installed."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        analyzer = SentimentIntensityAnalyzer()
        return float(analyzer.polarity_scores(text)["compound"])
    except ImportError:
        return _keyword_score(text)


BULLISH_WORDS = {
    "beat",
    "surged",
    "record",
    "upgrade",
    "bullish",
    "growth",
    "strong",
    "outperform",
    "buy",
    "rally",
    "gains",
    "positive",
    "raised",
    "exceeded",
}
BEARISH_WORDS = {
    "miss",
    "dropped",
    "downgrade",
    "bearish",
    "weak",
    "loss",
    "sell",
    "decline",
    "cut",
    "lower",
    "failed",
    "negative",
    "warning",
    "bankruptcy",
}


def _keyword_score(text: str) -> float:
    """Simple keyword-based sentiment fallback when VADER is unavailable."""
    words = set(re.findall(r"\b\w+\b", text.lower()))
    bull = len(words & BULLISH_WORDS)
    bear = len(words & BEARISH_WORDS)
    total = bull + bear
    if total == 0:
        return 0.0
    return (bull - bear) / total


class SentimentAnalyzer:
    """Multi-signal sentiment analysis for individual tickers and portfolios."""

    def analyze_ticker(self, ticker: str) -> Dict:
        """
        Compute a composite sentiment score for one ticker from:
        1. News headline sentiment (VADER or keyword scoring)
        2. Price momentum signal (SMA crossover)
        3. Volume trend signal
        4. RSI overbought/oversold signal
        """
        logger.info("Analyzing sentiment for %s", ticker)
        result: Dict = {"ticker": ticker, "signals": []}

        # -- 1. News sentiment -------------------------------------------------
        news_score = self._news_sentiment(ticker)
        result["signals"].append(news_score)

        # -- 2. Price momentum -------------------------------------------------
        momentum_score = self._momentum_signal(ticker)
        result["signals"].append(momentum_score)

        # -- 3. Volume trend ---------------------------------------------------
        volume_score = self._volume_signal(ticker)
        result["signals"].append(volume_score)

        # -- 4. RSI signal -----------------------------------------------------
        rsi_score = self._rsi_signal(ticker)
        result["signals"].append(rsi_score)

        # Composite (weighted average of signal scores)
        weights = {"news": 0.35, "momentum": 0.30, "volume": 0.15, "rsi": 0.20}
        total_w = 0.0
        composite = 0.0
        for sig in result["signals"]:
            w = weights.get(sig["type"], 0.0)
            composite += sig["score"] * w
            total_w += w
        composite = composite / total_w if total_w > 0 else 0.0

        result["composite_score"] = round(composite, 4)
        result["sentiment_label"] = (
            "BULLISH"
            if composite > 0.15
            else "BEARISH" if composite < -0.15 else "NEUTRAL"
        )
        result["confidence"] = self._confidence_level(result["signals"])
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        return result

    def _news_sentiment(self, ticker: str) -> Dict:
        """Fetch and score recent news headlines."""
        try:
            t = yf.Ticker(ticker)
            news = t.news or []
            if not news:
                return {
                    "type": "news",
                    "score": 0.0,
                    "label": "NEUTRAL",
                    "detail": "No news available",
                    "article_count": 0,
                }

            scores = []
            scored_articles = []
            for article in news[:10]:
                title = article.get("title", "")
                if not title:
                    continue
                score = _vader_score(title)
                scores.append(score)
                scored_articles.append({"title": title[:80], "score": round(score, 3)})

            avg = float(np.mean(scores)) if scores else 0.0
            return {
                "type": "news",
                "score": round(avg, 4),
                "label": (
                    "BULLISH" if avg > 0.05 else "BEARISH" if avg < -0.05 else "NEUTRAL"
                ),
                "article_count": len(scores),
                "sample_articles": scored_articles[:5],
            }
        except Exception as e:
            logger.warning("News fetch failed for %s: %s", ticker, e)
            return {"type": "news", "score": 0.0, "label": "NEUTRAL", "error": str(e)}

    def _momentum_signal(self, ticker: str) -> Dict:
        """SMA 20 vs SMA 50 crossover signal."""
        try:
            data = yf.download(ticker, period="3mo", progress=False, auto_adjust=True)[
                "Close"
            ]
            if isinstance(data, pd.DataFrame):
                data = data.iloc[:, 0]
            data = data.dropna()
            if len(data) < 50:
                return {
                    "type": "momentum",
                    "score": 0.0,
                    "label": "NEUTRAL",
                    "detail": "Insufficient data",
                }

            sma20 = float(data.tail(20).mean())
            sma50 = float(data.tail(50).mean())
            price = float(data.iloc[-1])
            diff_pct = (sma20 - sma50) / sma50

            score = np.clip(diff_pct * 10, -1.0, 1.0)
            return {
                "type": "momentum",
                "score": round(float(score), 4),
                "label": (
                    "BULLISH"
                    if score > 0.1
                    else "BEARISH" if score < -0.1 else "NEUTRAL"
                ),
                "sma_20": round(sma20, 4),
                "sma_50": round(sma50, 4),
                "current_price": round(price, 4),
                "golden_cross": sma20 > sma50,
            }
        except Exception as e:
            return {
                "type": "momentum",
                "score": 0.0,
                "label": "NEUTRAL",
                "error": str(e),
            }

    def _volume_signal(self, ticker: str) -> Dict:
        """Compare recent volume to 20-day average."""
        try:
            data = yf.download(ticker, period="2mo", progress=False, auto_adjust=True)
            if data.empty:
                return {"type": "volume", "score": 0.0, "label": "NEUTRAL"}
            vol = data["Volume"].dropna()
            price = data["Close"].dropna()
            if len(vol) < 20:
                return {
                    "type": "volume",
                    "score": 0.0,
                    "label": "NEUTRAL",
                    "detail": "Insufficient data",
                }

            avg_vol = float(vol.tail(20).mean())
            recent_vol = float(vol.iloc[-1])
            vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0
            price_change = float((price.iloc[-1] - price.iloc[-2]) / price.iloc[-2])

            # High volume + price up = bullish; high volume + price down = bearish
            score = np.clip((vol_ratio - 1.0) * np.sign(price_change), -1.0, 1.0)
            return {
                "type": "volume",
                "score": round(float(score), 4),
                "label": (
                    "BULLISH"
                    if score > 0.2
                    else "BEARISH" if score < -0.2 else "NEUTRAL"
                ),
                "volume_ratio_vs_avg": round(vol_ratio, 2),
                "price_change_pct": round(price_change * 100, 2),
            }
        except Exception as e:
            return {"type": "volume", "score": 0.0, "label": "NEUTRAL", "error": str(e)}

    def _rsi_signal(self, ticker: str) -> Dict:
        """RSI-14 overbought/oversold signal."""
        try:
            data = yf.download(ticker, period="3mo", progress=False, auto_adjust=True)[
                "Close"
            ]
            if isinstance(data, pd.DataFrame):
                data = data.iloc[:, 0]
            data = data.dropna()
            if len(data) < 15:
                return {"type": "rsi", "score": 0.0, "label": "NEUTRAL", "rsi": None}

            delta = data.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = float((100 - 100 / (1 + rs)).iloc[-1])

            if rsi > 70:
                score = -(rsi - 70) / 30  # overbought: negative signal
            elif rsi < 30:
                score = (30 - rsi) / 30  # oversold: positive signal
            else:
                score = 0.0

            return {
                "type": "rsi",
                "score": round(float(np.clip(score, -1, 1)), 4),
                "label": (
                    "OVERBOUGHT" if rsi > 70 else "OVERSOLD" if rsi < 30 else "NEUTRAL"
                ),
                "rsi_14": round(rsi, 2),
            }
        except Exception as e:
            return {"type": "rsi", "score": 0.0, "label": "NEUTRAL", "error": str(e)}

    @staticmethod
    def _confidence_level(signals: List[Dict]) -> str:
        scores = [s["score"] for s in signals if "score" in s]
        if not scores:
            return "low"
        agreement = sum(1 for s in scores if s > 0.1) or sum(
            1 for s in scores if s < -0.1
        )
        if agreement >= 3:
            return "high"
        if agreement >= 2:
            return "medium"
        return "low"

    def analyze_portfolio(self, tickers: List[str], weights: List[float]) -> Dict:
        """Aggregate sentiment across portfolio holdings, weighted by allocation."""
        results = []
        composite = 0.0
        for ticker, weight in zip(tickers, weights):
            try:
                r = self.analyze_ticker(ticker)
                r["portfolio_weight"] = round(weight, 4)
                r["weighted_score"] = round(r["composite_score"] * weight, 4)
                composite += r["composite_score"] * weight
                results.append(r)
            except Exception as e:
                logger.error("Sentiment failed for %s: %s", ticker, e)

        return {
            "portfolio_sentiment_score": round(composite, 4),
            "portfolio_sentiment_label": (
                "BULLISH"
                if composite > 0.1
                else "BEARISH" if composite < -0.1 else "NEUTRAL"
            ),
            "holdings": results,
            "most_bullish": max(
                results, key=lambda r: r["composite_score"], default=None
            ),
            "most_bearish": min(
                results, key=lambda r: r["composite_score"], default=None
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
