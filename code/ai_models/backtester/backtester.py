"""
QuantumWealth AI Models -- Backtesting Engine
============================================
Runs historical simulations of portfolio strategies with:
  - Transaction cost modeling (commissions + slippage)
  - Rebalancing trigger logic (threshold and calendar-based)
  - Benchmark comparison (alpha, beta, information ratio)
  - Detailed performance analytics (drawdown periods, rolling metrics)

Usage:
    engine = BacktestEngine()
    result = engine.run(
        tickers=["AAPL","MSFT","BND"],
        weights={"AAPL":0.4,"MSFT":0.4,"BND":0.2},
        start="2020-01-01", end="2024-01-01",
        rebalance_freq="quarterly",
        transaction_cost_bps=10,
    )
"""

from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger("ai_models.backtester")

REBALANCE_FREQS = {
    "monthly": "MS",
    "quarterly": "QS",
    "semiannual": "2QS",
    "annual": "YS",
    "never": None,
}


def _fetch_prices(tickers: List[str], start: str, end: str) -> pd.DataFrame:
    data = yf.download(tickers, start=start, end=end, progress=False, auto_adjust=True)[
        "Close"
    ]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    return data.ffill().dropna()


class BacktestEngine:
    """
    Event-driven portfolio backtest with daily granularity.
    Supports buy-and-hold, threshold rebalancing, and calendar rebalancing.
    """

    def run(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        start: str,
        end: str,
        initial_capital: float = 100_000.0,
        rebalance_freq: str = "quarterly",
        drift_threshold: float = 0.05,
        transaction_cost_bps: float = 10.0,
        benchmark_ticker: str = "SPY",
    ) -> Dict:
        logger.info("Starting backtest: %d tickers, %s to %s", len(tickers), start, end)
        cost_pct = transaction_cost_bps / 10_000

        all_tickers = list(set(tickers + [benchmark_ticker]))
        prices = _fetch_prices(all_tickers, start, end)
        if prices.empty:
            return {"error": "No price data for the specified period."}

        available = [t for t in tickers if t in prices.columns]
        if not available:
            return {"error": "None of the specified tickers have data."}

        target_w = np.array([weights.get(t, 0.0) for t in available])
        if target_w.sum() == 0:
            return {"error": "All weights are zero."}
        target_w /= target_w.sum()

        prices_port = prices[available]
        price_bmark = (
            prices[benchmark_ticker] if benchmark_ticker in prices.columns else None
        )

        # Determine rebalance dates
        freq = REBALANCE_FREQS.get(rebalance_freq, "QS")
        if freq:
            rebalance_dates = set(
                pd.date_range(
                    prices_port.index[0], prices_port.index[-1], freq=freq
                ).normalize()
            )
        else:
            rebalance_dates = {prices_port.index[0]}

        # Initialize portfolio
        shares = np.zeros(len(available))
        cash = initial_capital
        portfolio_values: List[float] = []
        dates: List[str] = []
        daily_returns: List[float] = []
        turnover_events: List[Dict] = []
        total_costs = 0.0

        for i, date in enumerate(prices_port.index):
            day_prices = prices_port.iloc[i].values

            # Portfolio value at open
            port_val = cash + float(np.sum(shares * day_prices))
            if i > 0:
                prev_val = portfolio_values[-1] if portfolio_values else initial_capital
                daily_ret = (port_val - prev_val) / prev_val if prev_val > 0 else 0.0
                daily_returns.append(daily_ret)
            portfolio_values.append(port_val)
            dates.append(str(date.date()))

            # Rebalance check
            should_rebalance = date.normalize() in rebalance_dates
            if not should_rebalance and drift_threshold > 0 and port_val > 0:
                current_w = (shares * day_prices) / port_val
                drift = np.max(np.abs(current_w - target_w))
                should_rebalance = drift >= drift_threshold

            if should_rebalance and port_val > 0:
                target_vals = target_w * port_val
                target_shares = target_vals / np.maximum(day_prices, 1e-8)
                trade_values = np.abs(target_shares - shares) * day_prices
                cost = float(np.sum(trade_values) * cost_pct)
                total_costs += cost
                shares = target_shares
                cash = 0.0
                port_val -= cost
                if trade_values.sum() > 0:
                    turnover_events.append(
                        {
                            "date": str(date.date()),
                            "turnover_pct": round(
                                float(trade_values.sum() / port_val * 100), 2
                            ),
                            "transaction_cost": round(cost, 2),
                        }
                    )

        port_series = pd.Series(portfolio_values, index=prices_port.index)
        ret_series = pd.Series([0.0] + daily_returns)

        # Performance metrics
        total_ret = (portfolio_values[-1] - initial_capital) / initial_capital
        n_days = len(daily_returns)
        ann_ret = (1 + total_ret) ** (252 / max(n_days, 1)) - 1
        ann_vol = float(ret_series.std() * np.sqrt(252))
        sharpe = (ann_ret - 0.05) / ann_vol if ann_vol > 0 else 0.0

        cumulative = (1 + ret_series).cumprod()
        roll_max = cumulative.cummax()
        dd_series = (cumulative - roll_max) / roll_max
        max_dd = float(dd_series.min())

        downside = ret_series[ret_series < 0]
        sortino_vol = (
            float(downside.std() * np.sqrt(252)) if len(downside) > 0 else ann_vol
        )
        sortino = (ann_ret - 0.05) / sortino_vol if sortino_vol > 0 else 0.0
        calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0.0

        # Benchmark comparison
        benchmark_metrics = {}
        if price_bmark is not None:
            bmark_ret = price_bmark.pct_change().dropna()
            bmark_aligned = bmark_ret.reindex(prices_port.index[1:]).fillna(0)
            port_aligned = pd.Series(daily_returns, index=prices_port.index[1:])
            cov_matrix = np.cov(port_aligned.values, bmark_aligned.values)
            beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] > 0 else 1.0
            bmark_ann_ret = float((1 + bmark_ret.mean()) ** 252 - 1)
            alpha = ann_ret - (0.05 + beta * (bmark_ann_ret - 0.05))
            tracking_error = float((port_aligned - bmark_aligned).std() * np.sqrt(252))
            info_ratio = alpha / tracking_error if tracking_error > 0 else 0.0
            benchmark_metrics = {
                "benchmark": benchmark_ticker,
                "benchmark_annualized_return": round(bmark_ann_ret, 4),
                "alpha": round(float(alpha), 4),
                "beta": round(float(beta), 4),
                "tracking_error": round(tracking_error, 4),
                "information_ratio": round(info_ratio, 4),
                "active_return": round(ann_ret - bmark_ann_ret, 4),
            }

        # Drawdown periods
        drawdown_periods = self._find_drawdown_periods(dd_series, prices_port.index)

        # Monthly returns table
        monthly_returns = self._compute_monthly_returns(port_series)

        return {
            "summary": {
                "start": dates[0],
                "end": dates[-1],
                "initial_capital": initial_capital,
                "final_value": round(portfolio_values[-1], 2),
                "total_return_pct": round(total_ret * 100, 2),
                "annualized_return": round(ann_ret, 4),
                "annualized_volatility": round(ann_vol, 4),
                "sharpe_ratio": round(sharpe, 4),
                "sortino_ratio": round(sortino, 4),
                "calmar_ratio": round(calmar, 4),
                "max_drawdown": round(max_dd, 4),
                "max_drawdown_pct": round(max_dd * 100, 2),
                "total_transaction_costs": round(total_costs, 2),
                "rebalance_count": len(turnover_events),
            },
            "benchmark_comparison": benchmark_metrics,
            "portfolio_history": [
                {"date": d, "value": round(v, 2)}
                for d, v in zip(
                    dates[::5], portfolio_values[::5]
                )  # sample every 5 days
            ],
            "drawdown_periods": drawdown_periods[:10],
            "monthly_returns": monthly_returns,
            "rebalance_events": turnover_events[:20],
            "settings": {
                "tickers": available,
                "target_weights": dict(zip(available, target_w.tolist())),
                "rebalance_freq": rebalance_freq,
                "drift_threshold": drift_threshold,
                "transaction_cost_bps": transaction_cost_bps,
            },
        }

    @staticmethod
    def _find_drawdown_periods(dd_series: pd.Series, index: pd.Index) -> List[Dict]:
        periods = []
        in_dd = False
        start_idx = 0
        for i, dd in enumerate(dd_series.values):
            if not in_dd and dd < -0.05:
                in_dd = True
                start_idx = i
            elif in_dd and dd >= -0.005:
                in_dd = False
                peak_dd = float(dd_series.iloc[start_idx:i].min())
                periods.append(
                    {
                        "start": str(index[start_idx].date()),
                        "end": str(index[i].date()),
                        "max_drawdown_pct": round(peak_dd * 100, 2),
                        "duration_days": i - start_idx,
                    }
                )
        return sorted(periods, key=lambda p: p["max_drawdown_pct"])

    @staticmethod
    def _compute_monthly_returns(port_series: pd.Series) -> List[Dict]:
        monthly = port_series.resample("ME").last().pct_change().dropna()
        return [
            {
                "year": int(d.year),
                "month": int(d.month),
                "return_pct": round(float(r * 100), 2),
            }
            for d, r in monthly.items()
        ]
