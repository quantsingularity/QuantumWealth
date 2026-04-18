"""Market service — yfinance-based quotes with Redis caching."""

import logging

import yfinance as yf
from django.core.cache import cache

logger = logging.getLogger("apps.market")

QUOTE_TTL = 60  # 1 minute for live quotes
HISTORY_TTL = 3600  # 1 hour for historical data
SEARCH_TTL = 3600  # 1 hour for search results


class MarketService:

    @staticmethod
    def _cache_key(*parts):
        return "market:" + ":".join(str(p) for p in parts)

    @classmethod
    def get_quote(cls, ticker: str) -> dict:
        key = cls._cache_key("quote", ticker)
        cached = cache.get(key)
        if cached:
            return cached

        try:
            t = yf.Ticker(ticker)
            info = t.fast_info
            result = {
                "ticker": ticker,
                "price": float(info.last_price) if info.last_price else None,
                "previous_close": (
                    float(info.previous_close) if info.previous_close else None
                ),
                "change": (
                    float(info.last_price - info.previous_close)
                    if (info.last_price and info.previous_close)
                    else None
                ),
                "change_pct": (
                    float(
                        ((info.last_price - info.previous_close) / info.previous_close)
                        * 100
                    )
                    if (
                        info.last_price
                        and info.previous_close
                        and info.previous_close != 0
                    )
                    else None
                ),
                "volume": (
                    int(info.three_month_average_volume)
                    if info.three_month_average_volume
                    else None
                ),
                "market_cap": int(info.market_cap) if info.market_cap else None,
                "52w_high": (
                    float(info.fifty_two_week_high)
                    if info.fifty_two_week_high
                    else None
                ),
                "52w_low": (
                    float(info.fifty_two_week_low) if info.fifty_two_week_low else None
                ),
            }
            # Try to get extra info
            try:
                full_info = t.info
                result["pe_ratio"] = full_info.get("trailingPE")
                result["dividend_yield"] = full_info.get("dividendYield")
                result["beta"] = full_info.get("beta")
                result["name"] = full_info.get("longName", "")
                result["sector"] = full_info.get("sector", "")
                result["industry"] = full_info.get("industry", "")
            except Exception:
                pass

            cache.set(key, result, QUOTE_TTL)
            return result
        except Exception as e:
            logger.error("Quote fetch failed for %s: %s", ticker, e)
            return {"ticker": ticker, "error": str(e)}

    @classmethod
    def get_quotes_bulk(cls, tickers: list) -> dict:
        """Fetch multiple quotes efficiently."""
        results = {}
        missing = []
        for ticker in tickers:
            key = cls._cache_key("quote", ticker)
            cached = cache.get(key)
            if cached:
                results[ticker] = cached
            else:
                missing.append(ticker)

        if missing:
            # Fetch all missing in one yfinance call
            try:
                data = yf.download(
                    missing, period="2d", progress=False, auto_adjust=True
                )["Close"]
                if hasattr(data, "columns"):
                    for ticker in missing:
                        if ticker in data.columns:
                            vals = data[ticker].dropna()
                            if len(vals) >= 2:
                                price = float(vals.iloc[-1])
                                prev = float(vals.iloc[-2])
                                result = {
                                    "ticker": ticker,
                                    "price": price,
                                    "previous_close": prev,
                                    "change": price - prev,
                                    "change_pct": (
                                        ((price - prev) / prev * 100)
                                        if prev != 0
                                        else 0
                                    ),
                                }
                                cache.set(
                                    cls._cache_key("quote", ticker), result, QUOTE_TTL
                                )
                                results[ticker] = result
            except Exception as e:
                logger.error("Bulk quote fetch failed: %s", e)
                for ticker in missing:
                    results[ticker] = cls.get_quote(ticker)
        return results

    @classmethod
    def get_history(cls, ticker: str, period: str = "1y", interval: str = "1d") -> dict:
        key = cls._cache_key("history", ticker, period, interval)
        cached = cache.get(key)
        if cached:
            return cached

        try:
            t = yf.Ticker(ticker)
            df = t.history(period=period, interval=interval)
            result = {
                "ticker": ticker,
                "period": period,
                "interval": interval,
                "data": [
                    {
                        "date": str(idx.date() if hasattr(idx, "date") else idx),
                        "open": round(float(row["Open"]), 4),
                        "high": round(float(row["High"]), 4),
                        "low": round(float(row["Low"]), 4),
                        "close": round(float(row["Close"]), 4),
                        "volume": int(row["Volume"]),
                    }
                    for idx, row in df.iterrows()
                ],
            }
            cache.set(key, result, HISTORY_TTL)
            return result
        except Exception as e:
            logger.error("History fetch failed for %s: %s", ticker, e)
            return {"ticker": ticker, "error": str(e)}

    @classmethod
    def predict(cls, ticker: str, horizon_days: int) -> dict:
        key = cls._cache_key("predict", ticker, horizon_days)
        cached = cache.get(key)
        if cached:
            return cached

        from ai_models.market_predictor import LSTMPredictor, RegimeDetector

        predictor = LSTMPredictor()
        prediction = predictor.predict(ticker, horizon_days)
        detector = RegimeDetector()
        regime = detector.detect(ticker)
        result = {**prediction, "regime": regime}
        cache.set(key, result, 1800)  # cache 30 min
        return result

    @classmethod
    def search(cls, query: str) -> list:
        key = cls._cache_key("search", query.lower().replace(" ", "_"))
        cached = cache.get(key)
        if cached:
            return cached

        try:
            results = yf.Search(query, max_results=10)
            output = [
                {
                    "ticker": r.get("symbol", ""),
                    "name": r.get("shortname", r.get("longname", "")),
                    "type": r.get("quoteType", ""),
                    "exchange": r.get("exchange", ""),
                }
                for r in results.quotes
                if r.get("symbol")
            ]
            cache.set(key, output, SEARCH_TTL)
            return output
        except Exception as e:
            logger.error("Search failed for '%s': %s", query, e)
            return []

    @classmethod
    def get_sector_performance(cls) -> dict:
        """Return YTD performance for major S&P 500 sector ETFs."""
        key = cls._cache_key("sectors")
        cached = cache.get(key)
        if cached:
            return cached

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
        results = {}
        try:
            tickers = list(SECTOR_ETFS.values())
            data = yf.download(tickers, period="ytd", progress=False, auto_adjust=True)[
                "Close"
            ]
            for sector, etf in SECTOR_ETFS.items():
                if etf in data.columns:
                    vals = data[etf].dropna()
                    if len(vals) >= 2:
                        ytd_return = (
                            (float(vals.iloc[-1]) - float(vals.iloc[0]))
                            / float(vals.iloc[0])
                            * 100
                        )
                        results[sector] = {
                            "ticker": etf,
                            "ytd_return_pct": round(ytd_return, 2),
                        }
        except Exception as e:
            logger.error("Sector performance fetch failed: %s", e)
        cache.set(key, results, 3600)
        return results
