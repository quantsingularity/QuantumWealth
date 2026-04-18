"""
Shared fixtures for AI model unit tests.

All fixtures use synthetic data (numpy-generated) so tests run
without network access or a live yfinance connection.
The yfinance download calls are patched at the module level in each test file.
"""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Synthetic return data
# ---------------------------------------------------------------------------

RNG = np.random.default_rng(42)
N_DAYS = 756  # ~3 years of trading days
DATE_INDEX = pd.bdate_range("2021-01-01", periods=N_DAYS)


def make_returns(
    tickers: list,
    mean: float = 0.0004,
    std: float = 0.012,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic daily log-returns for a list of tickers.
    Returns are correlated through a shared market factor.
    """
    rng = np.random.default_rng(seed)
    n = len(tickers)
    # Shared market factor
    market = rng.normal(mean, std, N_DAYS)
    idio = rng.normal(0, std * 0.6, (N_DAYS, n))
    returns_matrix = market[:, None] * 0.7 + idio * 0.3
    df = pd.DataFrame(returns_matrix, index=DATE_INDEX, columns=tickers)
    return df


def make_prices(tickers: list, start_price: float = 100.0) -> pd.DataFrame:
    """Reconstruct price series from synthetic returns."""
    returns = make_returns(tickers)
    prices = start_price * np.exp(returns.cumsum())
    return prices


def make_covariance(returns: pd.DataFrame) -> np.ndarray:
    return returns.cov().values * 252


def make_expected_returns(returns: pd.DataFrame) -> np.ndarray:
    return returns.mean().values * 252


# ---------------------------------------------------------------------------
# Standard test tickers and weights
# ---------------------------------------------------------------------------

TICKERS_4 = ["AAPL", "MSFT", "BND", "GLD"]
TICKERS_3 = ["SPY", "TLT", "GLD"]
WEIGHTS_4 = [0.30, 0.30, 0.25, 0.15]
WEIGHTS_3 = [0.60, 0.30, 0.10]

RETURNS_4 = make_returns(TICKERS_4)
RETURNS_3 = make_returns(TICKERS_3)
COV_4 = make_covariance(RETURNS_4)
MU_4 = make_expected_returns(RETURNS_4)
COV_3 = make_covariance(RETURNS_3)
MU_3 = make_expected_returns(RETURNS_3)

PRICES_4 = make_prices(TICKERS_4)

# ---------------------------------------------------------------------------
# Future date helpers
# ---------------------------------------------------------------------------


def future_datetime(years: float = 20.0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=int(years * 365))
