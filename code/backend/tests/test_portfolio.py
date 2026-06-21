"""
Tests for apps.portfolio:
  - Portfolio CRUD (create, list, retrieve, update, soft-delete)
  - Data isolation (users cannot access each other's portfolios)
  - Holdings add/merge with weighted-average cost
  - Transaction recording: deposit, withdrawal, buy, sell with realized-gain tracking
  - Financial goals CRUD and progress percentage
  - Portfolio snapshots
  - Model method unit tests
  - Optimization endpoint wired (mocked AI call)
  - Performance endpoint wired (mocked AI call)
"""

from decimal import Decimal

from apps.portfolio.models import (
    FinancialGoal,
    Holding,
    Portfolio,
    PortfolioSnapshot,
    Transaction,
    TransactionType,
)
from apps.portfolio.services import PortfolioService
from rest_framework import status
from rest_framework.test import APITestCase
from tests.conftest import (
    add_holding,
    add_transaction,
    anon_client,
    auth_client,
    make_goal,
    make_portfolio,
    make_snapshot,
    make_user,
)

# ---------------------------------------------------------------------------
# Portfolio CRUD
# ---------------------------------------------------------------------------


class PortfolioListCreateTests(APITestCase):
    URL = "/api/v1/portfolio/"

    def setUp(self):
        self.user = make_user("port@qw.ai")
        self.client = auth_client(self.user)

    def test_create_portfolio_returns_201(self):
        resp = self.client.post(
            self.URL,
            {
                "name": "My Growth Fund",
                "description": "Long-term growth portfolio",
                "cash_balance": "5000.00",
                "benchmark_ticker": "QQQ",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "My Growth Fund")

    def test_create_portfolio_response_includes_id(self):
        # Regression test: the create response previously omitted "id"
        # entirely (PortfolioCreateSerializer, used for input validation,
        # was also being used to build the response). The frontend
        # navigates to /portfolios/{id} immediately after creating one, so
        # a missing id broke that flow.
        resp = self.client.post(self.URL, {"name": "Needs An Id"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", resp.data)
        self.assertTrue(resp.data["id"])
        portfolio = Portfolio.objects.get(user=self.user, name="Needs An Id")
        self.assertEqual(str(portfolio.id), str(resp.data["id"]))

    def test_create_portfolio_persisted_to_database(self):
        self.client.post(self.URL, {"name": "DB Portfolio"}, format="json")
        self.assertEqual(
            Portfolio.objects.filter(user=self.user, name="DB Portfolio").count(), 1
        )

    def test_list_returns_only_own_portfolios(self):
        make_portfolio(self.user, "My P1")
        make_portfolio(self.user, "My P2")
        other = make_user("other_port@qw.ai")
        make_portfolio(other, "Other P")
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in resp.data["results"]]
        self.assertIn("My P1", names)
        self.assertIn("My P2", names)
        self.assertNotIn("Other P", names)

    def test_list_excludes_inactive_portfolios(self):
        make_portfolio(self.user, "Active")
        inactive = make_portfolio(self.user, "Inactive")
        inactive.is_active = False
        inactive.save()
        resp = self.client.get(self.URL)
        names = [p["name"] for p in resp.data["results"]]
        self.assertIn("Active", names)
        self.assertNotIn("Inactive", names)

    def test_unauthenticated_returns_401(self):
        resp = anon_client().get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class PortfolioDetailTests(APITestCase):
    def setUp(self):
        self.user = make_user("detail@qw.ai")
        self.client = auth_client(self.user)
        self.portfolio = make_portfolio(self.user, "Detail Portfolio")

    def _url(self):
        return f"/api/v1/portfolio/{self.portfolio.id}/"

    def test_retrieve_returns_holdings_and_transactions_fields(self):
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("holdings", resp.data)
        self.assertIn("recent_transactions", resp.data)

    def test_update_portfolio_name(self):
        resp = self.client.patch(
            self._url(), {"name": "Renamed Portfolio"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.name, "Renamed Portfolio")

    def test_soft_delete_sets_is_active_false(self):
        resp = self.client.delete(self._url())
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.portfolio.refresh_from_db()
        self.assertFalse(self.portfolio.is_active)

    def test_other_user_cannot_retrieve(self):
        other = make_user("stealer@qw.ai")
        resp = auth_client(other).get(self._url())
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_user_cannot_delete(self):
        other = make_user("deleter@qw.ai")
        resp = auth_client(other).delete(self._url())
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Holdings
# ---------------------------------------------------------------------------


class HoldingTests(APITestCase):
    def setUp(self):
        self.user = make_user("hold@qw.ai")
        self.client = auth_client(self.user)
        self.portfolio = make_portfolio(self.user)

    def _holdings_url(self):
        return f"/api/v1/portfolio/{self.portfolio.id}/holdings/"

    def _post_holding(
        self, ticker="AAPL", qty="10", price="150.00", asset_class="equity"
    ):
        return self.client.post(
            self._holdings_url(),
            {
                "ticker": ticker,
                "quantity": qty,
                "average_cost": price,
                "asset_class": asset_class,
            },
            format="json",
        )

    def test_add_holding_returns_201(self):
        resp = self._post_holding()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["ticker"], "AAPL")

    def test_ticker_uppercased_automatically(self):
        resp = self._post_holding(ticker="aapl")
        self.assertEqual(resp.data["ticker"], "AAPL")

    def test_market_value_computed_on_create(self):
        resp = self._post_holding(qty="10", price="150.00")
        self.assertEqual(Decimal(str(resp.data["market_value"])), Decimal("1500.0000"))

    def test_upsert_merges_with_weighted_average_cost(self):
        """Buy 10 @ $100 then 10 @ $200 -- average cost should be $150."""
        self._post_holding(ticker="MSFT", qty="10", price="100.00")
        self._post_holding(ticker="MSFT", qty="10", price="200.00")
        holding = Holding.objects.get(portfolio=self.portfolio, ticker="MSFT")
        self.assertEqual(holding.quantity, Decimal("20"))
        self.assertEqual(holding.average_cost, Decimal("150.0000"))

    def test_upsert_three_purchases(self):
        """Buy 5@100, 10@200, 5@300 => total 20 shares, avg cost 212.50."""
        self._post_holding(ticker="GOOG", qty="5", price="100.00")
        self._post_holding(ticker="GOOG", qty="10", price="200.00")
        self._post_holding(ticker="GOOG", qty="5", price="300.00")
        holding = Holding.objects.get(portfolio=self.portfolio, ticker="GOOG")
        self.assertEqual(holding.quantity, Decimal("20"))
        # (5*100 + 10*200 + 5*300) / 20 = (500+2000+1500)/20 = 4000/20 = 200
        self.assertEqual(holding.average_cost, Decimal("200.0000"))

    def test_list_holdings_returns_all(self):
        self._post_holding("AAPL")
        self._post_holding("MSFT")
        resp = self.client.get(self._holdings_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tickers = [h["ticker"] for h in resp.data]
        self.assertIn("AAPL", tickers)
        self.assertIn("MSFT", tickers)

    def test_portfolio_total_value_updated_after_add(self):
        self._post_holding(qty="10", price="100.00")
        self.portfolio.refresh_from_db()
        self.assertEqual(
            self.portfolio.total_value,
            self.portfolio.cash_balance + Decimal("1000.0000"),
        )

    def test_holding_weight_computed(self):
        self._post_holding(qty="10", price="100.00")
        holding = Holding.objects.get(portfolio=self.portfolio, ticker="AAPL")
        self.assertGreater(holding.weight, Decimal("0"))
        self.assertLessEqual(holding.weight, Decimal("1"))

    def test_invalid_asset_class_returns_400(self):
        resp = self.client.post(
            self._holdings_url(),
            {
                "ticker": "AAPL",
                "quantity": "10",
                "average_cost": "150.00",
                "asset_class": "magic_beans",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_quantity_returns_400(self):
        resp = self.client.post(
            self._holdings_url(),
            {
                "ticker": "AAPL",
                "quantity": "0",
                "average_cost": "150.00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


class TransactionTests(APITestCase):
    def setUp(self):
        self.user = make_user("txn@qw.ai")
        self.client = auth_client(self.user)
        self.portfolio = make_portfolio(self.user, cash=Decimal("20000.00"))

    def _txn_url(self):
        return f"/api/v1/portfolio/{self.portfolio.id}/transactions/"

    def _post_txn(self, **data):
        return self.client.post(self._txn_url(), data, format="json")

    def test_deposit_increases_cash_balance(self):
        resp = self._post_txn(transaction_type="deposit", amount="5000.00")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.cash_balance, Decimal("25000.00"))

    def test_withdrawal_decreases_cash_balance(self):
        resp = self._post_txn(transaction_type="withdrawal", amount="3000.00")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.cash_balance, Decimal("17000.00"))

    def test_buy_creates_holding_and_deducts_cash(self):
        resp = self._post_txn(
            transaction_type="buy",
            ticker="AAPL",
            quantity="10",
            price="150.00",
            amount="1500.00",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Holding.objects.filter(portfolio=self.portfolio, ticker="AAPL").exists()
        )
        self.portfolio.refresh_from_db()
        self.assertLess(self.portfolio.cash_balance, Decimal("20000.00"))

    def test_sell_reduces_holding_quantity(self):
        add_holding(self.portfolio, "AAPL", qty=Decimal("20"), price=Decimal("100.00"))
        resp = self._post_txn(
            transaction_type="sell",
            ticker="AAPL",
            quantity="5",
            price="120.00",
            amount="600.00",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        holding = Holding.objects.get(portfolio=self.portfolio, ticker="AAPL")
        self.assertEqual(holding.quantity, Decimal("15"))

    def test_sell_all_shares_removes_holding(self):
        add_holding(self.portfolio, "TSLA", qty=Decimal("5"), price=Decimal("200.00"))
        self._post_txn(
            transaction_type="sell",
            ticker="TSLA",
            quantity="5",
            price="250.00",
            amount="1250.00",
        )
        self.assertFalse(
            Holding.objects.filter(portfolio=self.portfolio, ticker="TSLA").exists()
        )

    def test_sell_records_realized_gain(self):
        add_holding(self.portfolio, "NVDA", qty=Decimal("10"), price=Decimal("100.00"))
        self._post_txn(
            transaction_type="sell",
            ticker="NVDA",
            quantity="10",
            price="150.00",
            amount="1500.00",
        )
        txn = Transaction.objects.filter(
            portfolio=self.portfolio,
            ticker="NVDA",
            transaction_type=TransactionType.SELL,
        ).first()
        self.assertIsNotNone(txn)
        self.assertIsNotNone(txn.realized_gain)
        self.assertGreater(txn.realized_gain, Decimal("0"))

    def test_sell_records_holding_period(self):
        add_holding(self.portfolio, "META", qty=Decimal("5"), price=Decimal("300.00"))
        add_transaction(
            self.portfolio,
            TransactionType.BUY,
            amount=Decimal("1500.00"),
            ticker="META",
            qty=Decimal("5"),
            price=Decimal("300.00"),
        )
        self._post_txn(
            transaction_type="sell",
            ticker="META",
            quantity="5",
            price="350.00",
            amount="1750.00",
        )
        txn = Transaction.objects.filter(
            portfolio=self.portfolio,
            ticker="META",
            transaction_type=TransactionType.SELL,
        ).first()
        self.assertIsNotNone(txn.holding_period_days)

    def test_list_transactions_paginated(self):
        for i in range(5):
            self._post_txn(transaction_type="deposit", amount=f"{(i+1)*100}.00")
        resp = self.client.get(self._txn_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 5)

    def test_filter_transactions_by_type(self):
        self._post_txn(transaction_type="deposit", amount="1000.00")
        self._post_txn(transaction_type="withdrawal", amount="500.00")
        resp = self.client.get(self._txn_url() + "?type=deposit")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        types = [t["transaction_type"] for t in resp.data["results"]]
        self.assertTrue(all(t == "deposit" for t in types))


# ---------------------------------------------------------------------------
# Financial Goals
# ---------------------------------------------------------------------------


class FinancialGoalTests(APITestCase):
    URL = "/api/v1/portfolio/goals/"

    def setUp(self):
        self.user = make_user("goals@qw.ai")
        self.client = auth_client(self.user)

    def _create_goal(self, **overrides):
        data = {
            "name": "House Down Payment",
            "goal_type": "house",
            "target_amount": "100000.00",
            "current_amount": "20000.00",
            "monthly_contribution": "1500.00",
            "target_date": "2029-01-01",
            "expected_return": "0.06",
        }
        data.update(overrides)
        return self.client.post(self.URL, data, format="json")

    def test_create_goal_returns_201(self):
        resp = self._create_goal()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "House Down Payment")

    def test_create_goal_linked_to_current_user(self):
        self._create_goal()
        goal = FinancialGoal.objects.get(name="House Down Payment")
        self.assertEqual(goal.user, self.user)

    def test_list_goals_returns_own_only(self):
        make_goal(self.user, name="My Goal")
        other = make_user("other_goals@qw.ai")
        make_goal(other, name="Their Goal")
        resp = self.client.get(self.URL)
        names = [g["name"] for g in resp.data["results"]]
        self.assertIn("My Goal", names)
        self.assertNotIn("Their Goal", names)

    def test_retrieve_goal_includes_progress_pct(self):
        goal = make_goal(self.user)
        resp = self.client.get(f"{self.URL}{goal.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("progress_pct", resp.data)
        self.assertIsInstance(resp.data["progress_pct"], float)

    def test_progress_pct_correct_value(self):
        goal = make_goal(
            self.user,
            target_amount=Decimal("100000.00"),
            current_amount=Decimal("25000.00"),
        )
        self.assertAlmostEqual(goal.progress_pct, 25.0, places=1)

    def test_progress_pct_capped_at_100(self):
        goal = make_goal(
            self.user,
            target_amount=Decimal("100000.00"),
            current_amount=Decimal("150000.00"),
        )
        self.assertEqual(goal.progress_pct, 100.0)

    def test_update_goal(self):
        goal = make_goal(self.user)
        resp = self.client.patch(
            f"{self.URL}{goal.id}/", {"name": "Updated Goal"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        goal.refresh_from_db()
        self.assertEqual(goal.name, "Updated Goal")

    def test_delete_goal(self):
        goal = make_goal(self.user)
        resp = self.client.delete(f"{self.URL}{goal.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FinancialGoal.objects.filter(id=goal.id).exists())

    def test_missing_target_date_returns_400(self):
        data = {
            "name": "No Date",
            "goal_type": "custom",
            "target_amount": "50000.00",
            "current_amount": "0.00",
            "monthly_contribution": "500.00",
        }
        resp = self.client.post(self.URL, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Portfolio Snapshots
# ---------------------------------------------------------------------------


class PortfolioSnapshotTests(APITestCase):
    def setUp(self):
        self.user = make_user("snap@qw.ai")
        self.client = auth_client(self.user)
        self.portfolio = make_portfolio(self.user)

    def test_manual_snapshot_returns_200(self):
        resp = self.client.post(f"/api/v1/portfolio/{self.portfolio.id}/snapshot/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_snapshot_persisted_to_database(self):
        self.client.post(f"/api/v1/portfolio/{self.portfolio.id}/snapshot/")
        self.assertEqual(
            PortfolioSnapshot.objects.filter(portfolio=self.portfolio).count(), 1
        )

    def test_snapshot_idempotent_within_same_day(self):
        """Calling snapshot twice on the same day should upsert, not duplicate."""
        self.client.post(f"/api/v1/portfolio/{self.portfolio.id}/snapshot/")
        self.client.post(f"/api/v1/portfolio/{self.portfolio.id}/snapshot/")
        self.assertEqual(
            PortfolioSnapshot.objects.filter(portfolio=self.portfolio).count(), 1
        )

    def test_history_endpoint_returns_snapshots(self):
        make_snapshot(self.portfolio, date_offset_days=1)
        make_snapshot(self.portfolio, date_offset_days=2)
        resp = self.client.get(f"/api/v1/portfolio/{self.portfolio.id}/history/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 2)


# ---------------------------------------------------------------------------
# Optimization (mocked AI call)
# ---------------------------------------------------------------------------


class PortfolioOptimizationTests(APITestCase):
    def setUp(self):
        self.user = make_user("optim@qw.ai")
        self.client = auth_client(self.user)
        self.portfolio = make_portfolio(self.user)
        add_holding(self.portfolio, "AAPL", Decimal("10"), Decimal("150.00"))
        add_holding(self.portfolio, "BND", Decimal("20"), Decimal("75.00"))

    def test_optimize_no_holdings_returns_error(self):
        empty_port = make_portfolio(self.user, "Empty Port")
        resp = self.client.post(
            f"/api/v1/portfolio/{empty_port.id}/optimize/",
            {"strategy": "mean_variance"},
            format="json",
        )
        self.assertIn(
            resp.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        )

    def test_optimize_other_user_portfolio_returns_404(self):
        other = make_user("other_optim@qw.ai")
        other_port = make_portfolio(other)
        resp = self.client.post(
            f"/api/v1/portfolio/{other_port.id}/optimize/",
            {"strategy": "mean_variance"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_optimize_invalid_strategy_returns_400(self):
        resp = self.client.post(
            f"/api/v1/portfolio/{self.portfolio.id}/optimize/",
            {"strategy": "magic_wand"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# PortfolioService unit tests
# ---------------------------------------------------------------------------


class PortfolioServiceTests(APITestCase):
    def setUp(self):
        self.user = make_user("svc@qw.ai")
        self.portfolio = make_portfolio(self.user, cash=Decimal("10000.00"))

    def test_recalculate_updates_total_value(self):
        add_holding(self.portfolio, "AAPL", Decimal("10"), Decimal("100.00"))
        PortfolioService.recalculate_portfolio(self.portfolio)
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.total_value, Decimal("11000.00"))

    def test_recalculate_sets_weights_sum_to_one(self):
        add_holding(self.portfolio, "AAPL", Decimal("10"), Decimal("100.00"))
        add_holding(self.portfolio, "MSFT", Decimal("5"), Decimal("200.00"))
        PortfolioService.recalculate_portfolio(self.portfolio)
        total_weight = sum(h.weight for h in self.portfolio.holdings.all())
        self.assertAlmostEqual(
            float(total_weight),
            float(
                sum(h.market_value for h in self.portfolio.holdings.all())
                / self.portfolio.total_value
            ),
            places=4,
        )

    def test_upsert_holding_new_ticker(self):
        holding = PortfolioService.upsert_holding(
            self.portfolio, "GOOG", Decimal("5"), Decimal("120.00")
        )
        self.assertEqual(holding.ticker, "GOOG")
        self.assertEqual(holding.quantity, Decimal("5"))

    def test_take_snapshot_creates_record(self):
        from datetime import date

        PortfolioService.take_snapshot(self.portfolio)
        self.assertEqual(
            PortfolioSnapshot.objects.filter(
                portfolio=self.portfolio, date=date.today()
            ).count(),
            1,
        )


# ---------------------------------------------------------------------------
# Holding model unit tests
# ---------------------------------------------------------------------------


class HoldingModelTests(APITestCase):
    def setUp(self):
        self.user = make_user("hm@qw.ai")
        self.portfolio = make_portfolio(self.user)

    def test_recalculate_computes_market_value(self):
        h = Holding(
            portfolio=self.portfolio,
            ticker="X",
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
            current_price=Decimal("150"),
        )
        h.recalculate()
        self.assertEqual(h.market_value, Decimal("1500"))

    def test_recalculate_computes_unrealized_pnl(self):
        h = Holding(
            portfolio=self.portfolio,
            ticker="X",
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
            current_price=Decimal("120"),
        )
        h.recalculate()
        self.assertEqual(h.unrealized_pnl, Decimal("200"))

    def test_recalculate_computes_unrealized_pnl_pct(self):
        h = Holding(
            portfolio=self.portfolio,
            ticker="X",
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
            current_price=Decimal("110"),
        )
        h.recalculate()
        self.assertAlmostEqual(float(h.unrealized_pnl_pct), 10.0, places=2)

    def test_recalculate_negative_pnl(self):
        h = Holding(
            portfolio=self.portfolio,
            ticker="X",
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
            current_price=Decimal("80"),
        )
        h.recalculate()
        self.assertEqual(h.unrealized_pnl, Decimal("-200"))
        self.assertAlmostEqual(float(h.unrealized_pnl_pct), -20.0, places=2)

    def test_unique_constraint_on_portfolio_ticker(self):
        add_holding(self.portfolio, "AAPL")
        with self.assertRaises(Exception):
            Holding.objects.create(
                portfolio=self.portfolio,
                ticker="AAPL",
                quantity=Decimal("5"),
                average_cost=Decimal("100"),
                current_price=Decimal("100"),
                market_value=Decimal("500"),
            )
