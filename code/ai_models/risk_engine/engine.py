"""
QuantumWealth AI Engine — Risk Engine
Implements: VaR (Historical & Parametric), CVaR, Monte Carlo GBM,
Stress Testing, Max Drawdown, Sharpe/Sortino/Calmar, Correlation Matrix.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

logger = logging.getLogger("ai_engine.risk_engine")

STRESS_SCENARIOS: Dict[str, Dict[str, float]] = {
    "2008_crisis": {
        "SPY": -0.565,
        "QQQ": -0.520,
        "TLT": 0.330,
        "GLD": 0.055,
        "EEM": -0.635,
        "IWM": -0.570,
        "AGG": 0.065,
        "VNQ": -0.700,
        "VTI": -0.560,
        "BND": 0.060,
        "XLF": -0.760,
        "XLK": -0.530,
    },
    "covid_crash": {
        "SPY": -0.340,
        "QQQ": -0.280,
        "TLT": 0.180,
        "GLD": 0.090,
        "EEM": -0.320,
        "IWM": -0.420,
        "AGG": 0.030,
        "VNQ": -0.420,
        "VTI": -0.340,
        "BND": 0.025,
        "XLF": -0.400,
        "XLK": -0.250,
    },
    "dot_com_bust": {
        "SPY": -0.490,
        "QQQ": -0.830,
        "TLT": 0.200,
        "GLD": 0.150,
        "EEM": -0.400,
        "IWM": -0.380,
        "AGG": 0.120,
        "VNQ": 0.110,
        "VTI": -0.480,
        "BND": 0.115,
        "XLF": -0.200,
        "XLK": -0.810,
    },
    "rate_shock": {
        "SPY": -0.150,
        "QQQ": -0.200,
        "TLT": -0.250,
        "GLD": -0.050,
        "EEM": -0.180,
        "IWM": -0.120,
        "AGG": -0.120,
        "VNQ": -0.200,
        "VTI": -0.145,
        "BND": -0.115,
        "XLF": -0.080,
        "XLK": -0.200,
    },
    "inflation_spike": {
        "SPY": -0.100,
        "QQQ": -0.180,
        "TLT": -0.300,
        "GLD": 0.200,
        "EEM": -0.100,
        "IWM": -0.080,
        "AGG": -0.140,
        "VNQ": -0.120,
        "VTI": -0.095,
        "BND": -0.130,
        "XLF": 0.050,
        "XLK": -0.150,
    },
}


def _fetch_returns(tickers: List[str], period: str = "3y") -> pd.DataFrame:
    data = yf.download(tickers, period=period, progress=False, auto_adjust=True)[
        "Close"
    ]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    data = data.dropna(how="all").ffill()
    returns = data.pct_change().dropna()
    return returns.dropna(axis=1, thresh=int(len(returns) * 0.8))


def _portfolio_returns(returns: pd.DataFrame, weights: np.ndarray) -> np.ndarray:
    available = returns.columns.tolist()
    w = np.array(weights)
    w = w / w.sum()
    return returns[available].values @ w


class RiskEngine:

    def compute_var(
        self,
        tickers: List[str],
        weights: List[float],
        portfolio_value: float,
        confidence: float = 0.95,
        horizon_days: int = 1,
        method: str = "historical",
    ) -> Dict:
        try:
            returns = _fetch_returns(tickers)
        except Exception as e:
            return {"error": str(e)}

        w = np.array(weights)
        port_ret = _portfolio_returns(returns, w)

        if method == "parametric":
            mu_daily = port_ret.mean()
            sigma_daily = port_ret.std()
            var_pct = float(stats.norm.ppf(1 - confidence, mu_daily, sigma_daily))
        else:  # historical
            var_pct = float(np.percentile(port_ret, (1 - confidence) * 100))

        var_scaled = var_pct * np.sqrt(horizon_days)
        var_dollar = abs(var_scaled) * portfolio_value

        threshold = np.percentile(port_ret, (1 - confidence) * 100)
        tail = port_ret[port_ret <= threshold]
        cvar_pct = float(tail.mean()) if len(tail) > 0 else var_pct
        cvar_scaled = cvar_pct * np.sqrt(horizon_days)
        cvar_dollar = abs(cvar_scaled) * portfolio_value

        return {
            "method": method,
            "confidence": confidence,
            "horizon_days": horizon_days,
            "var_pct": round(var_scaled * 100, 4),
            "var_dollar": round(var_dollar, 2),
            "cvar_pct": round(cvar_scaled * 100, 4),
            "cvar_dollar": round(cvar_dollar, 2),
            "portfolio_value": portfolio_value,
            "interpretation": (
                f"With {confidence:.0%} confidence, you will not lose more than "
                f"${var_dollar:,.0f} ({abs(var_scaled)*100:.2f}%) over {horizon_days} day(s)."
            ),
        }

    def stress_test(
        self,
        tickers: List[str],
        weights: List[float],
        portfolio_value: float,
        scenario: str = "2008_crisis",
    ) -> Dict:
        if scenario not in STRESS_SCENARIOS:
            return {
                "error": f"Unknown scenario '{scenario}'.",
                "available": list(STRESS_SCENARIOS.keys()),
            }

        shocks = STRESS_SCENARIOS[scenario]
        w = np.array(weights)
        w /= w.sum()

        position_impacts = []
        total_impact = 0.0
        for ticker, weight in zip(tickers, w):
            shock = shocks.get(ticker, -0.25)
            dollar_impact = portfolio_value * weight * shock
            position_impacts.append(
                {
                    "ticker": ticker,
                    "weight": round(float(weight), 4),
                    "scenario_return_pct": round(shock * 100, 2),
                    "dollar_impact": round(dollar_impact, 2),
                }
            )
            total_impact += dollar_impact

        position_impacts.sort(key=lambda x: x["dollar_impact"])

        return {
            "scenario": scenario,
            "portfolio_value": portfolio_value,
            "stressed_value": round(portfolio_value + total_impact, 2),
            "total_impact_dollar": round(total_impact, 2),
            "total_impact_pct": round((total_impact / portfolio_value) * 100, 2),
            "position_impacts": position_impacts,
        }

    def monte_carlo(
        self,
        tickers: List[str],
        weights: List[float],
        portfolio_value: float,
        simulations: int = 10_000,
        horizon_years: int = 10,
    ) -> Dict:
        try:
            returns = _fetch_returns(tickers)
        except Exception as e:
            return {"error": str(e)}

        w = np.array(weights)
        port_ret = _portfolio_returns(returns, w)
        mu_daily = port_ret.mean()
        sigma_daily = port_ret.std()
        trading_days = horizon_years * 252

        rng = np.random.default_rng(42)
        daily_rets = rng.normal(mu_daily, sigma_daily, (simulations, trading_days))
        paths = portfolio_value * np.cumprod(1 + daily_rets, axis=1)
        final_values = paths[:, -1]

        percentiles = {
            "p5": round(float(np.percentile(final_values, 5)), 2),
            "p10": round(float(np.percentile(final_values, 10)), 2),
            "p25": round(float(np.percentile(final_values, 25)), 2),
            "p50": round(float(np.percentile(final_values, 50)), 2),
            "p75": round(float(np.percentile(final_values, 75)), 2),
            "p90": round(float(np.percentile(final_values, 90)), 2),
            "p95": round(float(np.percentile(final_values, 95)), 2),
        }

        prob_profit = float((final_values > portfolio_value).mean())
        prob_double = float((final_values > portfolio_value * 2).mean())

        yearly_projections = []
        for yr in range(1, horizon_years + 1):
            idx = min(yr * 252 - 1, trading_days - 1)
            yearly_projections.append(
                {
                    "year": yr,
                    "p10": round(float(np.percentile(paths[:, idx], 10)), 2),
                    "p50": round(float(np.median(paths[:, idx])), 2),
                    "p90": round(float(np.percentile(paths[:, idx], 90)), 2),
                }
            )

        return {
            "simulations": simulations,
            "horizon_years": horizon_years,
            "initial_value": portfolio_value,
            "percentiles": percentiles,
            "probability_of_profit": round(prob_profit, 4),
            "probability_of_doubling": round(prob_double, 4),
            "expected_final_value": round(float(final_values.mean()), 2),
            "annualized_expected_return": round(float(mu_daily * 252), 4),
            "annualized_volatility": round(float(sigma_daily * np.sqrt(252)), 4),
            "yearly_projections": yearly_projections,
        }

    def full_report(
        self,
        tickers: List[str],
        weights: List[float],
        portfolio_value: float,
    ) -> Dict:
        try:
            returns = _fetch_returns(tickers)
        except Exception as e:
            return {"error": str(e)}

        w = np.array(weights)
        port_ret = _portfolio_returns(returns, w)

        ann_ret = float(port_ret.mean() * 252)
        ann_vol = float(port_ret.std() * np.sqrt(252))
        sharpe = (ann_ret - 0.05) / ann_vol if ann_vol > 0 else 0.0

        downside = port_ret[port_ret < 0]
        sortino_vol = (
            float(downside.std() * np.sqrt(252)) if len(downside) > 0 else ann_vol
        )
        sortino = (ann_ret - 0.05) / sortino_vol if sortino_vol > 0 else 0.0

        cumulative = (1 + port_ret).cumprod()
        rolling_max = cumulative.cummax()
        dd_series = (cumulative - rolling_max) / rolling_max
        max_dd = float(dd_series.min())
        calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0.0

        # Omega ratio
        threshold_daily = 0.05 / 252
        gains = port_ret[port_ret > threshold_daily] - threshold_daily
        losses = threshold_daily - port_ret[port_ret <= threshold_daily]
        omega = float(gains.sum() / losses.sum()) if losses.sum() > 0 else float("inf")

        var = self.compute_var(tickers, weights, portfolio_value)
        stress_results = {
            s: self.stress_test(tickers, weights, portfolio_value, s)[
                "total_impact_pct"
            ]
            for s in STRESS_SCENARIOS
        }

        return {
            "portfolio_value": portfolio_value,
            "performance": {
                "annualized_return": round(ann_ret, 4),
                "annualized_volatility": round(ann_vol, 4),
                "sharpe_ratio": round(sharpe, 4),
                "sortino_ratio": round(sortino, 4),
                "calmar_ratio": round(calmar, 4),
                "omega_ratio": round(omega, 4) if omega != float("inf") else None,
                "max_drawdown": round(max_dd, 4),
                "max_drawdown_pct": round(max_dd * 100, 2),
            },
            "risk_metrics": {
                "var_95_pct": var.get("var_pct"),
                "var_95_dollar": var.get("var_dollar"),
                "cvar_95_pct": var.get("cvar_pct"),
                "cvar_95_dollar": var.get("cvar_dollar"),
            },
            "stress_tests": stress_results,
        }

    def correlation_matrix(self, tickers: List[str]) -> Dict:
        """Compute pairwise correlation matrix for the given tickers."""
        try:
            returns = _fetch_returns(tickers)
        except Exception as e:
            return {"error": str(e)}

        corr = returns.corr().round(4)
        available = list(corr.columns)
        return {
            "tickers": available,
            "matrix": corr.values.tolist(),
            "labels": available,
            "high_correlations": [
                {
                    "ticker_a": t1,
                    "ticker_b": t2,
                    "correlation": round(float(corr.loc[t1, t2]), 4),
                }
                for i, t1 in enumerate(available)
                for t2 in available[i + 1 :]
                if abs(corr.loc[t1, t2]) > 0.80
            ],
        }
