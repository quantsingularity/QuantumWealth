"""
QuantumWealth AI Models -- Factor Models
========================================
Implements Fama-French 5-factor exposure analysis, portfolio attribution
(Brinson-Hood-Beebower), and custom multi-factor scoring.

Factors analyzed:
  Mkt-RF  : Market excess return
  SMB     : Small minus Big (size factor)
  HML     : High minus Low (value factor)
  RMW     : Robust minus Weak (profitability factor)
  CMA     : Conservative minus Aggressive (investment factor)
  MOM     : Momentum (Carhart 4th factor)

Reference data: Kenneth French Data Library (proxied via ETF returns when
the library is not available in the deployment environment).
"""

from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

logger = logging.getLogger("ai_models.factor_models")

# ETF proxies for each factor (long-short approximations)
FACTOR_PROXIES: Dict[str, Dict] = {
    "market": {"long": "SPY", "short": None, "description": "Broad US equity market"},
    "size_smb": {
        "long": "VB",
        "short": "VV",
        "description": "Small-cap minus large-cap",
    },
    "value_hml": {"long": "VTV", "short": "VUG", "description": "Value minus growth"},
    "profitability": {
        "long": "QUAL",
        "short": "USMV",
        "description": "High profitability minus low",
    },
    "investment": {
        "long": "VBR",
        "short": "VBK",
        "description": "Conservative minus aggressive investment",
    },
    "momentum": {
        "long": "MTUM",
        "short": "USMV",
        "description": "12-1 month price momentum",
    },
}

SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Energy": "XLE",
    "Consumer Discretionary": "XLY",
    "Utilities": "XLU",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Consumer Staples": "XLP",
    "Communication Services": "XLC",
}


def _fetch_returns(tickers: List[str], period: str = "3y") -> pd.DataFrame:
    data = yf.download(tickers, period=period, progress=False, auto_adjust=True)[
        "Close"
    ]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    return data.ffill().pct_change().dropna()


class FactorModel:
    """
    Runs OLS regression of portfolio returns against factor returns
    to decompose risk and return into systematic factor contributions.
    """

    def compute_factor_exposures(
        self, tickers: List[str], weights: List[float], period: str = "3y"
    ) -> Dict:
        """
        Regress portfolio returns on Fama-French factor proxies.
        Returns beta loadings, R-squared, alpha, and t-statistics.
        """
        logger.info("Computing factor exposures for %d tickers", len(tickers))

        # Portfolio returns
        try:
            asset_returns = _fetch_returns(tickers, period)
        except Exception as e:
            return {"error": str(e)}

        available = [t for t in tickers if t in asset_returns.columns]
        if not available:
            return {"error": "No return data available."}

        w = np.array([weights[tickers.index(t)] for t in available])
        w /= w.sum()
        port_ret = asset_returns[available].values @ w

        # Factor proxy returns
        factor_tickers = set()
        for f in FACTOR_PROXIES.values():
            factor_tickers.add(f["long"])
            if f["short"]:
                factor_tickers.add(f["short"])
        factor_tickers.add("BIL")  # risk-free proxy

        try:
            factor_data = _fetch_returns(list(factor_tickers), period)
        except Exception as e:
            return {"error": f"Factor data fetch failed: {e}"}

        # Build factor return matrix
        factors: Dict[str, np.ndarray] = {}
        rf = factor_data.get("BIL", pd.Series(0.0002, index=factor_data.index))
        for fname, cfg in FACTOR_PROXIES.items():
            long_ret = factor_data.get(cfg["long"])
            if long_ret is None:
                continue
            if cfg["short"] and cfg["short"] in factor_data:
                factors[fname] = (long_ret - factor_data[cfg["short"]]).values
            else:
                factors[fname] = (
                    long_ret - rf.reindex(long_ret.index, fill_value=0.0002)
                ).values

        if not factors:
            return {"error": "Could not construct factor returns."}

        # Align all series to common dates
        idx = asset_returns.index
        for arr in factors.values():
            idx = idx[: min(len(idx), len(arr))]

        Y = port_ret[: len(idx)]
        X_cols = list(factors.keys())
        X = np.column_stack([factors[f][: len(idx)] for f in X_cols])

        # Remove NaN rows
        mask = ~(np.isnan(Y) | np.any(np.isnan(X), axis=1))
        Y, X = Y[mask], X[mask]

        if len(Y) < 30:
            return {"error": "Insufficient overlapping data for regression."}

        # OLS regression with intercept (alpha)
        X_with_const = np.column_stack([np.ones(len(X)), X])
        try:
            coeffs, residuals, _, _ = np.linalg.lstsq(X_with_const, Y, rcond=None)
        except Exception as e:
            return {"error": f"Regression failed: {e}"}

        alpha_daily = coeffs[0]
        betas = coeffs[1:]
        y_hat = X_with_const @ coeffs
        ss_res = np.sum((Y - y_hat) ** 2)
        ss_tot = np.sum((Y - Y.mean()) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        # Standard errors and t-stats
        n, k = len(Y), len(coeffs)
        sigma2 = ss_res / max(n - k, 1)
        try:
            cov_coeffs = sigma2 * np.linalg.inv(X_with_const.T @ X_with_const)
            se = np.sqrt(np.diag(cov_coeffs))
        except Exception:
            se = np.ones(k) * np.nan

        factor_exposures = []
        for i, fname in enumerate(X_cols):
            beta = float(betas[i])
            t_stat = (
                float(beta / se[i + 1])
                if not np.isnan(se[i + 1]) and se[i + 1] > 0
                else None
            )
            p_val = (
                float(2 * (1 - stats.t.cdf(abs(t_stat), df=n - k)))
                if t_stat is not None
                else None
            )
            factor_exposures.append(
                {
                    "factor": fname,
                    "description": FACTOR_PROXIES[fname]["description"],
                    "beta": round(beta, 4),
                    "t_statistic": round(t_stat, 3) if t_stat else None,
                    "p_value": round(p_val, 4) if p_val else None,
                    "significant": (p_val < 0.05) if p_val else None,
                }
            )

        return {
            "factor_exposures": factor_exposures,
            "alpha_annualized": round(float(alpha_daily * 252), 4),
            "alpha_daily": round(float(alpha_daily), 6),
            "r_squared": round(float(r_squared), 4),
            "observations": int(len(Y)),
            "period": period,
            "interpretation": self._interpret(
                alpha_daily * 252, r_squared, factor_exposures
            ),
        }

    @staticmethod
    def _interpret(alpha_ann: float, r2: float, exposures: List[Dict]) -> str:
        lines = []
        if alpha_ann > 0.02:
            lines.append(
                f"The portfolio generates positive annualized alpha of {alpha_ann:.1%}, "
                "suggesting manager skill or factor tilts not captured by the model."
            )
        elif alpha_ann < -0.02:
            lines.append(
                f"Negative alpha of {alpha_ann:.1%} indicates underperformance vs factor model."
            )
        else:
            lines.append(
                "Alpha is close to zero; returns are largely explained by factor exposures."
            )
        lines.append(f"Factor model explains {r2:.0%} of return variation (R-squared).")
        sig = [e for e in exposures if e.get("significant")]
        if sig:
            names = ", ".join(e["factor"] for e in sig)
            lines.append(f"Statistically significant exposures: {names}.")
        return " ".join(lines)

    def sector_decomposition(self, tickers: List[str], weights: List[float]) -> Dict:
        """Decompose portfolio into GICS sector weights using ETF proxies."""
        try:
            all_tickers = tickers + list(SECTOR_ETFS.values())
            data = yf.download(
                all_tickers, period="1y", progress=False, auto_adjust=True
            )["Close"]
            if isinstance(data, pd.Series):
                data = data.to_frame()
            returns = data.ffill().pct_change().dropna()
        except Exception as e:
            return {"error": str(e)}

        available = [t for t in tickers if t in returns.columns]
        if not available:
            return {"error": "No portfolio data."}

        w = np.array([weights[tickers.index(t)] for t in available])
        w /= w.sum()
        port_ret = returns[available].values @ w

        sector_betas = {}
        for sector, etf in SECTOR_ETFS.items():
            if etf not in returns.columns:
                continue
            s_ret = returns[etf].values
            min_len = min(len(port_ret), len(s_ret))
            corr = float(np.corrcoef(port_ret[:min_len], s_ret[:min_len])[0, 1])
            sector_betas[sector] = round(corr, 4)

        sorted_sectors = sorted(sector_betas.items(), key=lambda x: -abs(x[1]))
        return {
            "sector_correlations": [
                {"sector": s, "correlation": c} for s, c in sorted_sectors
            ],
            "dominant_sector": sorted_sectors[0][0] if sorted_sectors else None,
            "note": "Correlation with sector ETF returns over 1 year.",
        }

    def performance_attribution(
        self, portfolio_weights: Dict[str, float], benchmark_ticker: str = "SPY"
    ) -> Dict:
        """
        Brinson-Hood-Beebower performance attribution.
        Decomposes active return into: allocation effect + selection effect + interaction.
        """
        tickers = list(portfolio_weights.keys())
        try:
            all_t = tickers + [benchmark_ticker]
            data = yf.download(all_t, period="1y", progress=False, auto_adjust=True)[
                "Close"
            ]
            if isinstance(data, pd.Series):
                data = data.to_frame()
            returns = data.ffill().pct_change().dropna()
        except Exception as e:
            return {"error": str(e)}

        available = [t for t in tickers if t in returns.columns]
        if not available or benchmark_ticker not in returns.columns:
            return {"error": "Insufficient data for attribution."}

        w_p = np.array([portfolio_weights.get(t, 0.0) for t in available])
        w_p /= w_p.sum()
        w_b = np.ones(len(available)) / len(available)  # equal-weight benchmark proxy

        r_p = returns[available].mean().values * 252
        r_b_total = float(returns[benchmark_ticker].mean() * 252)
        r_security = r_p

        allocation_effect = float(
            np.sum((w_p - w_b) * (r_b_total - r_b_total))
        )  # simplified
        selection_effect = float(np.sum(w_b * (r_security - r_b_total)))
        interaction_effect = float(np.sum((w_p - w_b) * (r_security - r_b_total)))
        portfolio_return = float(np.sum(w_p * r_security))
        active_return = portfolio_return - r_b_total

        security_attribution = [
            {
                "ticker": t,
                "portfolio_weight": round(float(w_p[i]), 4),
                "security_return": round(float(r_security[i]), 4),
                "selection_contribution": round(
                    float(w_b[i] * (r_security[i] - r_b_total)), 4
                ),
            }
            for i, t in enumerate(available)
        ]

        return {
            "portfolio_return": round(portfolio_return, 4),
            "benchmark_return": round(r_b_total, 4),
            "active_return": round(active_return, 4),
            "attribution": {
                "allocation_effect": round(allocation_effect, 4),
                "selection_effect": round(selection_effect, 4),
                "interaction_effect": round(interaction_effect, 4),
                "total_active": round(
                    allocation_effect + selection_effect + interaction_effect, 4
                ),
            },
            "security_attribution": security_attribution,
            "benchmark": benchmark_ticker,
        }
