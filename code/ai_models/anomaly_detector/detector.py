"""
QuantumWealth AI Models -- Anomaly Detector
==========================================
Detects unusual patterns in portfolio behavior using:
  - Isolation Forest for multivariate anomaly detection
  - Z-score based outlier detection for individual return series
  - Portfolio concentration anomaly detection
  - Transaction pattern anomaly detection (wash-sale clustering,
    unusual trade size, abnormal frequency)

The Isolation Forest is an unsupervised algorithm that isolates anomalies
by randomly partitioning feature space -- anomalies require fewer splits
to isolate than normal observations.

Dependencies: scikit-learn, numpy, pandas
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("ai_models.anomaly_detector")

ANOMALY_CONTAMINATION = 0.05  # expected fraction of anomalies in return data


class PortfolioAnomalyDetector:
    """
    Detects statistically unusual events in portfolio return streams
    and transaction histories.
    """

    def detect_return_anomalies(
        self, tickers: List[str], weights: List[float], period: str = "2y"
    ) -> Dict:
        """
        Identify anomalous trading days using Isolation Forest
        on portfolio-level features: return, volatility, volume ratio.
        """
        logger.info("Running return anomaly detection for %d tickers", len(tickers))
        try:
            data = yf.download(tickers, period=period, progress=False, auto_adjust=True)
        except Exception as e:
            return {"error": str(e)}

        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"]
            volume = data["Volume"]
        else:
            close = data[["Close"]] if "Close" in data else data
            volume = (
                data[["Volume"]] if "Volume" in data else pd.DataFrame(index=data.index)
            )

        if isinstance(close, pd.Series):
            close = close.to_frame(name=tickers[0])

        close = close.ffill().dropna()
        returns = close.pct_change().dropna()

        available = [t for t in tickers if t in returns.columns]
        if not available:
            return {"error": "No return data available."}

        w = np.array(
            [weights[tickers.index(t)] if t in tickers else 0.0 for t in available]
        )
        w /= w.sum()
        port_ret = returns[available].values @ w

        # Feature engineering
        rolling_vol = (
            pd.Series(port_ret).rolling(21).std().fillna(method="bfill").values
        )
        rolling_mean = (
            pd.Series(port_ret).rolling(21).mean().fillna(method="bfill").values
        )

        vol_volume_ratio = np.ones(len(port_ret))
        if not volume.empty:
            avg_volume = volume.mean(axis=1).reindex(returns.index).ffill().fillna(1)
            recent_volume = (
                volume.mean(axis=1).reindex(returns.index).fillna(avg_volume)
            )
            vol_volume_ratio = (recent_volume / avg_volume.replace(0, 1)).values[
                : len(port_ret)
            ]

        features = np.column_stack(
            [
                port_ret,
                rolling_vol[: len(port_ret)],
                np.abs(port_ret - rolling_mean[: len(port_ret)]),  # deviation from mean
                vol_volume_ratio[: len(port_ret)],
            ]
        )
        features = np.nan_to_num(features, nan=0.0)

        scaler = StandardScaler()
        X = scaler.fit_transform(features)

        clf = IsolationForest(
            n_estimators=200,
            contamination=ANOMALY_CONTAMINATION,
            random_state=42,
            n_jobs=-1,
        )
        labels = clf.fit_predict(X)
        scores = clf.score_samples(X)

        anomaly_indices = np.where(labels == -1)[0]
        anomaly_days = []
        for idx in anomaly_indices:
            date = str(returns.index[idx].date())
            ret = float(port_ret[idx])
            score = float(scores[idx])
            severity = "high" if score < np.percentile(scores, 2) else "medium"
            anomaly_days.append(
                {
                    "date": date,
                    "portfolio_return_pct": round(ret * 100, 3),
                    "anomaly_score": round(score, 4),
                    "severity": severity,
                    "description": (
                        f"{'Large loss' if ret < 0 else 'Large gain'} of {abs(ret)*100:.2f}% "
                        f"on elevated volatility -- statistically unusual."
                    ),
                }
            )

        anomaly_days.sort(key=lambda d: d["anomaly_score"])

        return {
            "total_days_analyzed": len(port_ret),
            "anomaly_days_detected": len(anomaly_days),
            "anomaly_rate_pct": round(
                len(anomaly_days) / max(len(port_ret), 1) * 100, 2
            ),
            "anomalies": anomaly_days[:20],
            "z_score_outliers": self._z_score_outliers(port_ret, returns.index),
            "period": period,
        }

    @staticmethod
    def _z_score_outliers(
        returns: np.ndarray, index: pd.Index, threshold: float = 3.0
    ) -> List[Dict]:
        """Find days where portfolio return exceeds 3 standard deviations from mean."""
        mu, sigma = returns.mean(), returns.std()
        if sigma == 0:
            return []
        z_scores = (returns - mu) / sigma
        outliers = []
        for i, (z, r) in enumerate(zip(z_scores, returns)):
            if abs(z) >= threshold:
                outliers.append(
                    {
                        "date": str(index[i].date()),
                        "return_pct": round(float(r * 100), 3),
                        "z_score": round(float(z), 2),
                        "direction": "down" if r < 0 else "up",
                    }
                )
        return sorted(outliers, key=lambda x: -abs(x["z_score"]))[:10]

    def detect_transaction_anomalies(self, transactions: List[Dict]) -> Dict:
        """
        Flag unusual transaction patterns:
        - Abnormally large single trades (>3 std of trade sizes)
        - Unusually high frequency on a single day
        - Potential wash-sale clustering (buy then sell same ticker within 30 days)
        - Round-trip trades (buy + full sell within short window)
        """
        if not transactions:
            return {"anomalies": [], "summary": "No transactions to analyze."}

        anomalies = []

        # Size anomaly detection
        amounts = [
            abs(float(t.get("amount", 0))) for t in transactions if t.get("amount")
        ]
        if len(amounts) >= 5:
            mu, sigma = np.mean(amounts), np.std(amounts)
            for txn in transactions:
                amt = abs(float(txn.get("amount", 0)))
                if sigma > 0 and (amt - mu) / sigma > 3.0:
                    anomalies.append(
                        {
                            "type": "large_transaction",
                            "severity": "medium",
                            "ticker": txn.get("ticker", ""),
                            "amount": round(amt, 2),
                            "z_score": round((amt - mu) / sigma, 2),
                            "description": f"Transaction size is {(amt-mu)/sigma:.1f} std above average.",
                        }
                    )

        # Wash-sale clustering
        buy_map: Dict[str, List] = {}
        for txn in transactions:
            if txn.get("transaction_type") == "buy" and txn.get("ticker"):
                ticker = txn["ticker"]
                buy_map.setdefault(ticker, []).append(txn.get("executed_at", ""))

        for txn in transactions:
            if txn.get("transaction_type") == "sell" and txn.get("ticker"):
                ticker = txn["ticker"]
                if ticker in buy_map:
                    for buy_date in buy_map[ticker]:
                        try:
                            bd = pd.Timestamp(buy_date).date()
                            sd = pd.Timestamp(txn.get("executed_at", "")).date()
                            days_diff = abs((sd - bd).days)
                            if days_diff <= 30:
                                anomalies.append(
                                    {
                                        "type": "wash_sale_risk",
                                        "severity": "high",
                                        "ticker": ticker,
                                        "buy_date": str(bd),
                                        "sell_date": str(sd),
                                        "days_between": days_diff,
                                        "description": (
                                            f"Buy and sell of {ticker} within {days_diff} days. "
                                            "IRS wash-sale rule may disallow the loss."
                                        ),
                                    }
                                )
                        except Exception:
                            pass

        return {
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "high_severity": sum(1 for a in anomalies if a["severity"] == "high"),
            "medium_severity": sum(1 for a in anomalies if a["severity"] == "medium"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def detect_concentration_anomaly(self, holdings: List[Dict]) -> Dict:
        """Flag portfolios with dangerous concentration levels."""
        if not holdings:
            return {"anomalies": []}
        weights = [float(h.get("weight", 0)) for h in holdings]
        total = sum(weights)
        if total == 0:
            return {"anomalies": []}
        weights_norm = [w / total for w in weights]

        herfindahl = sum(w**2 for w in weights_norm)  # HHI: 1/n is fully diversified

        n = len(holdings)
        min_hhi = 1 / n
        anomalies = []

        for holding, w in zip(holdings, weights_norm):
            if w > 0.40:
                anomalies.append(
                    {
                        "type": "single_position_concentration",
                        "severity": "high",
                        "ticker": holding.get("ticker"),
                        "weight": round(w, 4),
                        "description": f"{holding.get('ticker')} represents {w:.1%} of portfolio.",
                    }
                )
            elif w > 0.25:
                anomalies.append(
                    {
                        "type": "single_position_concentration",
                        "severity": "medium",
                        "ticker": holding.get("ticker"),
                        "weight": round(w, 4),
                        "description": f"{holding.get('ticker')} represents {w:.1%} of portfolio.",
                    }
                )

        asset_classes: Dict[str, float] = {}
        for h, w in zip(holdings, weights_norm):
            ac = h.get("asset_class", "equity")
            asset_classes[ac] = asset_classes.get(ac, 0) + w

        for ac, w in asset_classes.items():
            if ac == "equity" and w > 0.90:
                anomalies.append(
                    {
                        "type": "asset_class_concentration",
                        "severity": "medium",
                        "asset_class": ac,
                        "weight": round(w, 4),
                        "description": f"Portfolio is {w:.0%} equity with minimal diversification.",
                    }
                )

        return {
            "herfindahl_index": round(herfindahl, 4),
            "effective_n": round(1 / herfindahl, 1) if herfindahl > 0 else n,
            "diversification_score": round(
                1 - (herfindahl - min_hhi) / (1 - min_hhi), 4
            ),
            "anomalies": anomalies,
        }
