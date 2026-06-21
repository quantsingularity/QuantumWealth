"""
QuantumWealth AI Models -- Portfolio Optimizer
==============================================
Strategies: Mean-Variance, Black-Litterman, Risk Parity, Hierarchical Risk Parity (HRP).
"""

from __future__ import annotations

import logging
import warnings

import cvxpy as cp
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform

warnings.filterwarnings("ignore")
logger = logging.getLogger("ai_models.portfolio_optimizer")


def fetch_returns(tickers, period="2y"):
    data = yf.download(tickers, period=period, progress=False, auto_adjust=True)[
        "Close"
    ]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    returns = np.log(data.ffill() / data.ffill().shift(1)).dropna()
    return returns.dropna(axis=1, thresh=int(len(returns) * 0.8))


def annualize(returns):
    return returns.mean().values * 252, returns.cov().values * 252


def mean_variance_optimize(
    tickers, mu, sigma, target_return=None, max_weight=0.40, min_weight=0.01
):
    n = len(tickers)
    w = cp.Variable(n)
    constraints = [cp.sum(w) == 1, w >= min_weight, w <= max_weight]
    if target_return is not None:
        constraints.append(mu @ w >= target_return)
        prob = cp.Problem(cp.Minimize(cp.quad_form(w, cp.psd_wrap(sigma))), constraints)
    else:
        prob = cp.Problem(
            cp.Maximize(mu @ w - 0.5 * cp.quad_form(w, cp.psd_wrap(sigma))), constraints
        )
    # FIX: ECOS is not bundled with recent cvxpy releases and is not installed
    # in this environment, which raised SolverError on every call. CLARABEL is
    # cvxpy's modern default conic solver and ships with the cvxpy package.
    prob.solve(solver=cp.CLARABEL)
    weights = (
        np.clip(w.value, 0, 1)
        if prob.status in ["optimal", "optimal_inaccurate"] and w.value is not None
        else np.ones(n) / n
    )
    weights /= weights.sum()
    ret = float(mu @ weights)
    vol = float(np.sqrt(max(weights @ sigma @ weights, 0)))
    return {
        "weights": dict(zip(tickers, weights.tolist())),
        "expected_return": round(ret, 4),
        "expected_volatility": round(vol, 4),
        "sharpe_ratio": round((ret - 0.05) / vol if vol > 1e-8 else 0, 4),
    }


def black_litterman_optimize(
    tickers, mu, sigma, market_caps=None, views=None, view_confidence=0.5
):
    n = len(tickers)
    tau = 0.05
    w_mkt = (
        np.array([market_caps.get(t, 1.0) for t in tickers])
        / sum(market_caps.get(t, 1.0) for t in tickers)
        if market_caps
        else np.ones(n) / n
    )
    pi = 3.0 * sigma @ w_mkt
    posterior_mu = pi
    if views:
        vt = [t for t in tickers if t in views]
        if vt:
            P = np.zeros((len(vt), n))
            Q = np.array([views[t] for t in vt])
            for i, t in enumerate(vt):
                P[i, tickers.index(t)] = 1.0
            omega = np.diag(np.diag(P @ (tau * sigma) @ P.T)) / view_confidence
            st = tau * sigma
            M = np.linalg.inv(np.linalg.inv(st) + P.T @ np.linalg.inv(omega) @ P)
            posterior_mu = M @ (np.linalg.inv(st) @ pi + P.T @ np.linalg.inv(omega) @ Q)
    result = mean_variance_optimize(tickers, posterior_mu, sigma)
    result["model"] = "black_litterman"
    return result


def risk_parity_optimize(tickers, sigma):
    n = len(tickers)
    w = cp.Variable(n, pos=True)
    # FIX: cp.sqrt(cp.quad_form(...)) is not recognized as convex by cvxpy's
    # DCP ruleset (raises DCPError), even though sqrt of a PSD quadratic form
    # is mathematically a norm. The standard equal-risk-contribution convex
    # reformulation (Maillard, Roncalli & Teiletche 2010) drops the square
    # root entirely: minimizing 0.5 * w^T Sigma w - (1/n) * sum(log(w_i))
    # yields the same equal-risk-contribution solution and is DCP-compliant.
    prob = cp.Problem(
        cp.Minimize(0.5 * cp.quad_form(w, cp.psd_wrap(sigma)) - cp.sum(cp.log(w)) / n),
        [cp.sum(w) == 1, w >= 0.005, w <= 0.50],
    )
    prob.solve(solver=cp.CLARABEL)
    weights = (
        np.clip(w.value, 0, 1)
        if prob.status in ["optimal", "optimal_inaccurate"] and w.value is not None
        else np.ones(n) / n
    )
    weights /= weights.sum()
    vol = float(np.sqrt(max(weights @ sigma @ weights, 0)))
    ret = float(np.mean(np.sqrt(np.diag(sigma))) * 0.5)
    return {
        "weights": dict(zip(tickers, weights.tolist())),
        "expected_return": round(ret, 4),
        "expected_volatility": round(vol, 4),
        "sharpe_ratio": round((ret - 0.05) / vol if vol > 0 else 0, 4),
        "model": "risk_parity",
    }


def hrp_optimize(tickers, returns):
    """Hierarchical Risk Parity (Lopez de Prado 2016). Clusters assets by correlation
    then recursively allocates weights by inverse cluster variance."""
    n = len(tickers)
    cov = returns.cov().values * 252
    corr = np.clip(returns.corr().values, -1, 1)
    np.fill_diagonal(corr, 1.0)
    dist = squareform(np.sqrt(np.clip((1 - corr) / 2, 0, 1)))
    link = linkage(dist, method="single")

    # Quasi-diagonalize: get leaf sort order
    def get_order(lnk, n):
        items = [int(lnk[-1, 0]), int(lnk[-1, 1])]
        while len(items) < n:
            new = []
            for x in items:
                new += [int(lnk[x - n, 0]), int(lnk[x - n, 1])] if x >= n else [x]
            items = new
        return [x for x in items if x < n]

    order = get_order(link, n)

    # Recursive bisection
    weights = np.ones(n)
    clusters = [order]
    while clusters:
        new_c = []
        for cl in clusters:
            if len(cl) <= 1:
                continue
            half = len(cl) // 2
            left, right = cl[:half], cl[half:]

            def cv(idx):
                w_sub = weights[idx]
                return max(float(w_sub @ cov[np.ix_(idx, idx)] @ w_sub), 1e-12)

            alpha = 1 - cv(left) / (cv(left) + cv(right))
            weights[left] *= alpha
            weights[right] *= 1 - alpha
            new_c += [left, right]
        clusters = new_c

    weights /= weights.sum()
    vol = float(np.sqrt(max(weights @ cov @ weights, 0)))
    ret = float(returns.mean().values @ weights * 252)
    return {
        "weights": dict(zip(tickers, weights.tolist())),
        "expected_return": round(ret, 4),
        "expected_volatility": round(vol, 4),
        "sharpe_ratio": round((ret - 0.05) / vol if vol > 0 else 0, 4),
        "model": "hrp",
    }


def compute_efficient_frontier(tickers, mu, sigma, points=30, max_weight=0.40):
    targets = np.linspace(float(mu.min()) + 0.001, float(mu.max()) - 0.001, points)
    frontier = []
    for t in targets:
        try:
            r = mean_variance_optimize(
                tickers, mu, sigma, target_return=t, max_weight=max_weight
            )
            frontier.append(
                {
                    "target_return": round(t, 4),
                    "volatility": round(r["expected_volatility"], 4),
                    "sharpe": round(r["sharpe_ratio"], 4),
                }
            )
        except Exception:
            pass
    return frontier


class PortfolioOptimizer:
    def optimize(
        self,
        tickers,
        strategy="mean_variance",
        current_weights=None,
        risk_tolerance=0.5,
        target_return=None,
        max_weight=0.40,
        constraints=None,
    ):
        try:
            returns = fetch_returns(tickers)
        except Exception as e:
            return {"error": str(e)}
        if returns.empty:
            return {"error": "No data available."}
        tc = list(returns.columns)
        mu, sigma = annualize(returns)
        max_w = float((constraints or {}).get("max_weight", max_weight))
        if strategy == "black_litterman":
            result = black_litterman_optimize(
                tc, mu, sigma, views=(constraints or {}).get("views")
            )
        elif strategy == "risk_parity":
            result = risk_parity_optimize(tc, sigma)
        elif strategy == "hrp":
            result = hrp_optimize(tc, returns)
        else:
            result = mean_variance_optimize(
                tc, mu, sigma, target_return=target_return, max_weight=max_w
            )
        cw = current_weights or {}
        allocations = sorted(
            [
                {
                    "ticker": t,
                    "current_weight": round(cw.get(t, 0.0), 4),
                    "target_weight": round(w, 4),
                    "suggested_action": (
                        "BUY"
                        if w - cw.get(t, 0.0) > 0.005
                        else "SELL" if w - cw.get(t, 0.0) < -0.005 else "HOLD"
                    ),
                    "weight_change": round(w - cw.get(t, 0.0), 4),
                }
                for t, w in result["weights"].items()
            ],
            key=lambda a: -abs(a["weight_change"]),
        )
        return {
            "strategy": strategy,
            "expected_return": result["expected_return"],
            "expected_volatility": result["expected_volatility"],
            "sharpe_ratio": result["sharpe_ratio"],
            "allocations": allocations,
            "efficient_frontier": compute_efficient_frontier(
                tc, mu, sigma, max_weight=max_w
            ),
            "metadata": {
                "tickers_used": tc,
                "tickers_dropped": [t for t in tickers if t not in tc],
                "data_period": "2y",
            },
        }
