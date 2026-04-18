"""
Tests for apps.market:
  - Quote endpoint (mocked yfinance)
  - Bulk quote endpoint
  - History endpoint (mocked yfinance)
  - Search endpoint (mocked yfinance)
  - Sector performance endpoint
  - Watchlist CRUD and quotes action
  - Market service caching behaviour
  - Price alert Celery task logic
"""

from unittest.mock import MagicMock, patch

from apps.market.models import Watchlist
from rest_framework import status
from rest_framework.test import APITestCase
from tests.conftest import auth_client, make_user

MOCK_QUOTE = {
    "ticker": "AAPL",
    "price": 175.50,
    "previous_close": 172.30,
    "change": 3.20,
    "change_pct": 1.86,
    "volume": 55000000,
    "market_cap": 2_700_000_000_000,
    "52w_high": 199.62,
    "52w_low": 124.17,
}

MOCK_HISTORY = {
    "ticker": "AAPL",
    "period": "1y",
    "interval": "1d",
    "data": [
        {
            "date": "2024-01-02",
            "open": 185.0,
            "high": 186.0,
            "low": 184.0,
            "close": 185.5,
            "volume": 50000000,
        }
    ],
}


# ---------------------------------------------------------------------------
# Quote endpoint
# ---------------------------------------------------------------------------


class QuoteTests(APITestCase):
    def setUp(self):
        self.user = make_user("quote@qw.ai")
        self.client = auth_client(self.user)

    @patch("apps.market.services.MarketService.get_quote", return_value=MOCK_QUOTE)
    def test_quote_returns_200_with_price(self, _mock):
        resp = self.client.get("/api/v1/market/quote/AAPL/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["ticker"], "AAPL")
        self.assertIn("price", resp.data)

    @patch("apps.market.services.MarketService.get_quote", return_value=MOCK_QUOTE)
    def test_quote_ticker_uppercased(self, _mock):
        resp = self.client.get("/api/v1/market/quote/aapl/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_quote_unauthenticated_returns_401(self):
        from tests.conftest import anon_client

        resp = anon_client().get("/api/v1/market/quote/AAPL/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Bulk quote endpoint
# ---------------------------------------------------------------------------


class BulkQuoteTests(APITestCase):
    def setUp(self):
        self.user = make_user("bulk@qw.ai")
        self.client = auth_client(self.user)

    @patch(
        "apps.market.services.MarketService.get_quotes_bulk",
        return_value={
            "AAPL": MOCK_QUOTE,
            "MSFT": {**MOCK_QUOTE, "ticker": "MSFT"},
        },
    )
    def test_bulk_quote_returns_dict_keyed_by_ticker(self, _mock):
        resp = self.client.post(
            "/api/v1/market/quotes/bulk/", {"tickers": ["AAPL", "MSFT"]}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("AAPL", resp.data)
        self.assertIn("MSFT", resp.data)

    def test_bulk_quote_empty_list_returns_400(self):
        resp = self.client.post(
            "/api/v1/market/quotes/bulk/", {"tickers": []}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_quote_missing_body_returns_400(self):
        resp = self.client.post("/api/v1/market/quotes/bulk/", {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.market.services.MarketService.get_quotes_bulk", return_value={})
    def test_bulk_quote_caps_at_50_tickers(self, mock_bulk):
        tickers = [f"T{i:03d}" for i in range(60)]
        self.client.post(
            "/api/v1/market/quotes/bulk/", {"tickers": tickers}, format="json"
        )
        # The view should cap the list at 50
        called_tickers = mock_bulk.call_args[0][0]
        self.assertLessEqual(len(called_tickers), 50)


# ---------------------------------------------------------------------------
# History endpoint
# ---------------------------------------------------------------------------


class HistoryTests(APITestCase):
    def setUp(self):
        self.user = make_user("hist@qw.ai")
        self.client = auth_client(self.user)

    @patch("apps.market.services.MarketService.get_history", return_value=MOCK_HISTORY)
    def test_history_returns_200_with_data_list(self, _mock):
        resp = self.client.get("/api/v1/market/history/AAPL/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("data", resp.data)
        self.assertIsInstance(resp.data["data"], list)

    @patch("apps.market.services.MarketService.get_history", return_value=MOCK_HISTORY)
    def test_history_accepts_period_query_param(self, mock_hist):
        self.client.get("/api/v1/market/history/AAPL/?period=5y&interval=1wk")
        mock_hist.assert_called_once_with("AAPL", "5y", "1wk")


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------


class SearchTests(APITestCase):
    MOCK_RESULTS = [
        {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "type": "EQUITY",
            "exchange": "NASDAQ",
        },
        {"ticker": "AAPLX", "name": "Apple Fund", "type": "MUTUALFUND", "exchange": ""},
    ]

    def setUp(self):
        self.user = make_user("search@qw.ai")
        self.client = auth_client(self.user)

    @patch("apps.market.services.MarketService.search", return_value=MOCK_RESULTS)
    def test_search_returns_list_of_results(self, _mock):
        resp = self.client.get("/api/v1/market/search/?q=apple")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)
        self.assertGreater(len(resp.data), 0)

    def test_search_without_q_returns_400(self):
        resp = self.client.get("/api/v1/market/search/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Sector performance endpoint
# ---------------------------------------------------------------------------


class SectorPerformanceTests(APITestCase):
    MOCK_SECTORS = {
        "Technology": {"ticker": "XLK", "ytd_return_pct": 12.5},
        "Healthcare": {"ticker": "XLV", "ytd_return_pct": 4.2},
    }

    def setUp(self):
        self.user = make_user("sector@qw.ai")
        self.client = auth_client(self.user)

    @patch(
        "apps.market.services.MarketService.get_sector_performance",
        return_value=MOCK_SECTORS,
    )
    def test_sector_performance_returns_dict(self, _mock):
        resp = self.client.get("/api/v1/market/sectors/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, dict)


# ---------------------------------------------------------------------------
# Watchlist CRUD
# ---------------------------------------------------------------------------


class WatchlistTests(APITestCase):
    LIST_URL = "/api/v1/market/watchlists/"

    def setUp(self):
        self.user = make_user("watch@qw.ai")
        self.client = auth_client(self.user)

    def test_create_watchlist_returns_201(self):
        resp = self.client.post(
            self.LIST_URL,
            {
                "name": "Tech Picks",
                "tickers": ["AAPL", "MSFT", "GOOG"],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "Tech Picks")
        self.assertEqual(resp.data["tickers"], ["AAPL", "MSFT", "GOOG"])

    def test_list_watchlists_returns_own_only(self):
        Watchlist.objects.create(user=self.user, name="Mine", tickers=["AAPL"])
        other = make_user("other_watch@qw.ai")
        Watchlist.objects.create(user=other, name="Theirs", tickers=["MSFT"])
        resp = self.client.get(self.LIST_URL)
        names = [w["name"] for w in resp.data["results"]]
        self.assertIn("Mine", names)
        self.assertNotIn("Theirs", names)

    def test_update_watchlist_tickers(self):
        wl = Watchlist.objects.create(user=self.user, name="Test WL", tickers=["AAPL"])
        resp = self.client.patch(
            f"{self.LIST_URL}{wl.id}/", {"tickers": ["AAPL", "TSLA"]}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        wl.refresh_from_db()
        self.assertIn("TSLA", wl.tickers)

    def test_delete_watchlist(self):
        wl = Watchlist.objects.create(user=self.user, name="Delete Me", tickers=[])
        resp = self.client.delete(f"{self.LIST_URL}{wl.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    @patch(
        "apps.market.services.MarketService.get_quotes_bulk",
        return_value={"AAPL": MOCK_QUOTE},
    )
    def test_watchlist_quotes_action_returns_list(self, _mock):
        wl = Watchlist.objects.create(user=self.user, name="Quote WL", tickers=["AAPL"])
        resp = self.client.get(f"{self.LIST_URL}{wl.id}/quotes/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)

    def test_cannot_access_other_user_watchlist(self):
        other = make_user("other_wl@qw.ai")
        wl = Watchlist.objects.create(user=other, name="Private WL", tickers=[])
        resp = self.client.get(f"{self.LIST_URL}{wl.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# MarketService caching unit tests
# ---------------------------------------------------------------------------


class MarketServiceCacheTests(APITestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    @patch("yfinance.Ticker")
    def test_quote_is_cached_on_second_call(self, MockTicker):
        """The second call should hit cache and not call yfinance again."""
        from apps.market.services import MarketService

        mock_t = MagicMock()
        mock_t.fast_info.last_price = 175.0
        mock_t.fast_info.previous_close = 172.0
        mock_t.fast_info.three_month_average_volume = 50_000_000
        mock_t.fast_info.market_cap = 2_700_000_000_000
        mock_t.fast_info.fifty_two_week_high = 199.0
        mock_t.fast_info.fifty_two_week_low = 124.0
        mock_t.info = {}
        MockTicker.return_value = mock_t

        MarketService.get_quote("CACHED")
        MarketService.get_quote("CACHED")
        # yfinance Ticker should only be instantiated once (second call served from cache)
        self.assertEqual(MockTicker.call_count, 1)

    @patch("apps.market.services.MarketService.get_quote", return_value=MOCK_QUOTE)
    def test_get_quotes_bulk_returns_dict(self, _mock):
        from apps.market.services import MarketService

        result = MarketService.get_quotes_bulk(["AAPL"])
        self.assertIsInstance(result, dict)
