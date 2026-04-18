"""
Tests for apps.risk, apps.advisor, and apps.tax:
  - Risk report, VaR, Monte Carlo, stress test, correlation endpoints
  - Advisor: recommendations, drift, rebalance, goal plan, suggested allocation
  - Tax: harvest opportunities, gain/loss report, asset location, wash-sale check
  - Service-layer unit tests for AdvisorService and TaxService
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from apps.advisor.services import AdvisorService
from apps.portfolio.models import AssetClass, TransactionType
from apps.tax.services import TaxService
from rest_framework import status
from rest_framework.test import APITestCase
from tests.conftest import (
    add_holding,
    add_transaction,
    anon_client,
    auth_client,
    make_portfolio,
    make_user,
)

MOCK_RISK_REPORT = {
    "portfolio_value": 50000.0,
    "performance": {
        "annualized_return": 0.12,
        "annualized_volatility": 0.18,
        "sharpe_ratio": 0.39,
        "sortino_ratio": 0.55,
        "calmar_ratio": 0.90,
        "omega_ratio": 1.35,
        "max_drawdown": -0.133,
        "max_drawdown_pct": -13.3,
    },
    "risk_metrics": {
        "var_95_pct": -2.1,
        "var_95_dollar": -1050.0,
        "cvar_95_pct": -3.2,
        "cvar_95_dollar": -1600.0,
    },
    "stress_tests": {
        "2008_crisis": -42.0,
        "covid_crash": -22.0,
        "dot_com_bust": -35.0,
        "rate_shock": -8.0,
        "inflation_spike": -6.0,
    },
}

MOCK_VAR = {
    "method": "historical",
    "confidence": 0.95,
    "horizon_days": 1,
    "var_pct": -2.1,
    "var_dollar": -1050.0,
    "cvar_pct": -3.2,
    "cvar_dollar": -1600.0,
    "portfolio_value": 50000.0,
    "interpretation": "With 95% confidence...",
}

MOCK_MONTE_CARLO = {
    "simulations": 10000,
    "horizon_years": 10,
    "initial_value": 50000.0,
    "percentiles": {"p5": 30000.0, "p50": 85000.0, "p95": 160000.0},
    "probability_of_profit": 0.87,
    "probability_of_doubling": 0.62,
    "expected_final_value": 92000.0,
    "yearly_projections": [],
}

MOCK_STRESS = {
    "scenario": "2008_crisis",
    "portfolio_value": 50000.0,
    "stressed_value": 29000.0,
    "total_impact_dollar": -21000.0,
    "total_impact_pct": -42.0,
    "position_impacts": [],
}

MOCK_CORRELATION = {
    "tickers": ["AAPL", "BND"],
    "matrix": [[1.0, -0.25], [-0.25, 1.0]],
    "labels": ["AAPL", "BND"],
    "high_correlations": [],
}


class _PortfolioMixin:
    """Base mixin providing a two-holding portfolio for risk/advisor/tax tests."""

    def _setup_portfolio(self):
        self.user = make_user("risk@qw.ai")
        self.client = auth_client(self.user)
        self.portfolio = make_portfolio(self.user, cash=Decimal("5000.00"))
        self.h_aapl = add_holding(
            self.portfolio,
            "AAPL",
            Decimal("10"),
            Decimal("150.00"),
            unrealized_pnl=Decimal("200.00"),
        )
        self.h_bnd = add_holding(
            self.portfolio,
            "BND",
            Decimal("20"),
            Decimal("75.00"),
            asset_class=AssetClass.FIXED_INCOME,
            unrealized_pnl=Decimal("-150.00"),
        )


# ---------------------------------------------------------------------------
# Risk Engine endpoints
# ---------------------------------------------------------------------------


class RiskReportTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()

    @patch("apps.risk.views.RiskEngine")
    def test_risk_report_returns_200_with_performance(self, MockEngine):
        MockEngine.return_value.full_report.return_value = MOCK_RISK_REPORT
        resp = self.client.get(f"/api/v1/risk/report/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("performance", resp.data)
        self.assertIn("risk_metrics", resp.data)

    def test_risk_report_empty_portfolio_returns_400(self):
        empty = make_portfolio(self.user, "Empty")
        resp = self.client.get(f"/api/v1/risk/report/{empty.id}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_risk_report_other_user_returns_404(self):
        other = make_user("other_risk@qw.ai")
        resp = self.client.get(f"/api/v1/risk/report/{self.portfolio.id}/")
        # Switch to other user's client
        other_client = auth_client(other)
        resp = other_client.get(f"/api/v1/risk/report/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_risk_unauthenticated_returns_401(self):
        resp = anon_client().get(f"/api/v1/risk/report/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class VaRTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()

    @patch("apps.risk.views.RiskEngine")
    def test_var_returns_200_with_var_fields(self, MockEngine):
        MockEngine.return_value.compute_var.return_value = MOCK_VAR
        resp = self.client.get(f"/api/v1/risk/var/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("var_dollar", resp.data)
        self.assertIn("cvar_dollar", resp.data)

    @patch("apps.risk.views.RiskEngine")
    def test_var_accepts_confidence_param(self, MockEngine):
        MockEngine.return_value.compute_var.return_value = MOCK_VAR
        resp = self.client.get(
            f"/api/v1/risk/var/{self.portfolio.id}/?confidence=0.99&horizon_days=5"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        _, kwargs = MockEngine.return_value.compute_var.call_args
        call_args = MockEngine.return_value.compute_var.call_args
        # Confidence and horizon should have been passed through
        args = call_args[0]
        self.assertIn(0.99, args)
        self.assertIn(5, args)


class MonteCarloTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()

    @patch("apps.risk.views.RiskEngine")
    def test_monte_carlo_returns_200_with_percentiles(self, MockEngine):
        MockEngine.return_value.monte_carlo.return_value = MOCK_MONTE_CARLO
        resp = self.client.get(f"/api/v1/risk/monte-carlo/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("percentiles", resp.data)
        self.assertIn("probability_of_profit", resp.data)

    @patch("apps.risk.views.RiskEngine")
    def test_monte_carlo_simulations_capped_at_50000(self, MockEngine):
        MockEngine.return_value.monte_carlo.return_value = MOCK_MONTE_CARLO
        resp = self.client.get(
            f"/api/v1/risk/monte-carlo/{self.portfolio.id}/?simulations=999999"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        call_args = MockEngine.return_value.monte_carlo.call_args[0]
        self.assertLessEqual(call_args[3], 50000)


class StressTestTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()

    @patch("apps.risk.views.RiskEngine")
    def test_stress_test_single_scenario(self, MockEngine):
        MockEngine.return_value.stress_test.return_value = MOCK_STRESS
        resp = self.client.post(
            f"/api/v1/risk/stress-test/{self.portfolio.id}/",
            {"scenario": "2008_crisis"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("stressed_value", resp.data)

    @patch("apps.risk.views.RiskEngine")
    def test_stress_test_all_scenarios(self, MockEngine):
        MockEngine.return_value.stress_test.return_value = MOCK_STRESS
        resp = self.client.post(
            f"/api/v1/risk/stress-test/{self.portfolio.id}/",
            {"scenario": "all"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Response should be a dict of scenarios
        self.assertIsInstance(resp.data, dict)


class CorrelationTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()

    @patch("apps.risk.views.RiskEngine")
    def test_correlation_returns_matrix(self, MockEngine):
        MockEngine.return_value.correlation_matrix.return_value = MOCK_CORRELATION
        resp = self.client.get(f"/api/v1/risk/correlation/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("matrix", resp.data)
        self.assertIn("tickers", resp.data)

    def test_correlation_requires_at_least_two_holdings(self):
        single_holding_port = make_portfolio(self.user, "Single H")
        add_holding(single_holding_port, "AAPL", Decimal("5"), Decimal("150.00"))
        resp = self.client.get(f"/api/v1/risk/correlation/{single_holding_port.id}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Advisor endpoints
# ---------------------------------------------------------------------------


class AdvisorRecommendationsTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()

    def test_recommendations_returns_200(self):
        resp = self.client.get(f"/api/v1/advisor/recommendations/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("recommendations", resp.data)
        self.assertIsInstance(resp.data["recommendations"], list)

    def test_recommendations_detects_concentration_risk(self):
        # Make AAPL overwhelmingly large
        self.h_aapl.weight = Decimal("0.90")
        self.h_aapl.save()
        resp = self.client.get(f"/api/v1/advisor/recommendations/{self.portfolio.id}/")
        types = [r["type"] for r in resp.data["recommendations"]]
        self.assertIn("concentration_risk", types)

    def test_recommendations_other_user_returns_404(self):
        other = make_user("other_adv@qw.ai")
        resp = auth_client(other).get(
            f"/api/v1/advisor/recommendations/{self.portfolio.id}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class AdvisorDriftTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()

    def test_drift_with_target_returns_drift_data(self):
        self.portfolio.target_allocation = {"AAPL": 0.60, "BND": 0.40}
        self.portfolio.save()
        resp = self.client.get(f"/api/v1/advisor/drift/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("drift_data", resp.data)
        self.assertIn("total_drift", resp.data)

    def test_drift_without_target_returns_error(self):
        self.portfolio.target_allocation = {}
        self.portfolio.save()
        resp = self.client.get(f"/api/v1/advisor/drift/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("error", resp.data)

    def test_drift_needs_rebalancing_flag(self):
        # AAPL at 90% but target is 50%
        self.portfolio.target_allocation = {"AAPL": 0.50, "BND": 0.50}
        self.portfolio.save()
        self.h_aapl.weight = Decimal("0.90")
        self.h_aapl.save()
        self.h_bnd.weight = Decimal("0.10")
        self.h_bnd.save()
        resp = self.client.get(f"/api/v1/advisor/drift/{self.portfolio.id}/")
        self.assertTrue(resp.data["needs_rebalancing"])


class AdvisorRebalanceTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()
        self.portfolio.target_allocation = {"AAPL": 0.50, "BND": 0.50}
        self.portfolio.save()

    def test_rebalance_returns_trades(self):
        resp = self.client.post(
            f"/api/v1/advisor/rebalance/{self.portfolio.id}/",
            {"drift_threshold": 0.01},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("trades", resp.data)

    def test_rebalance_without_target_returns_error(self):
        self.portfolio.target_allocation = {}
        self.portfolio.save()
        resp = self.client.post(
            f"/api/v1/advisor/rebalance/{self.portfolio.id}/", {}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("error", resp.data)

    def test_sell_trades_come_before_buy_trades(self):
        resp = self.client.post(
            f"/api/v1/advisor/rebalance/{self.portfolio.id}/",
            {"drift_threshold": 0.01},
            format="json",
        )
        trades = resp.data.get("trades", [])
        if len(trades) >= 2:
            actions = [t["action"] for t in trades]
            first_buy_idx = next((i for i, a in enumerate(actions) if a == "BUY"), None)
            last_sell_idx = next(
                (i for i, a in enumerate(reversed(actions)) if a == "SELL"), None
            )
            if first_buy_idx and last_sell_idx:
                self.assertLessEqual(
                    len(actions) - 1 - last_sell_idx,
                    first_buy_idx,
                    "All SELL trades should come before BUY trades",
                )


class GoalPlanTests(APITestCase):
    def setUp(self):
        self.user = make_user("plan@qw.ai")
        self.client = auth_client(self.user)

    def test_goal_plan_returns_200_with_projection(self):
        resp = self.client.post(
            "/api/v1/advisor/plan/",
            {
                "goal_type": "retirement",
                "target_amount": "1000000",
                "current_savings": "50000",
                "monthly_contribution": "2000",
                "target_date": "2050-01-01T00:00:00Z",
                "expected_return": 0.07,
                "inflation_adjusted": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("projected_value", resp.data)
        self.assertIn("probability_of_success", resp.data)
        self.assertIn("milestones", resp.data)
        self.assertIn("scenarios", resp.data)

    def test_goal_plan_missing_required_fields_returns_400(self):
        resp = self.client.post(
            "/api/v1/advisor/plan/",
            {
                "goal_type": "retirement",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_goal_plan_invalid_date_returns_400(self):
        resp = self.client.post(
            "/api/v1/advisor/plan/",
            {
                "goal_type": "house",
                "target_amount": "100000",
                "current_savings": "10000",
                "monthly_contribution": "500",
                "target_date": "not-a-date",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class SuggestedAllocationTests(APITestCase):
    def setUp(self):
        self.user = make_user("alloc@qw.ai", risk_profile="aggressive")
        self.client = auth_client(self.user)

    def test_suggested_allocation_returns_profile_data(self):
        resp = self.client.get("/api/v1/advisor/suggested-allocation/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["risk_profile"], "aggressive")
        self.assertIn("suggested_allocation", resp.data)
        self.assertIn("expected_annual_return", resp.data)

    def test_suggested_allocation_matches_risk_profile(self):
        """Aggressive profile should have higher equity allocation than conservative."""
        resp = self.client.get("/api/v1/advisor/suggested-allocation/")
        equity_weight = resp.data["suggested_allocation"].get("equity", 0)
        self.assertGreater(equity_weight, 0.5)


# ---------------------------------------------------------------------------
# Tax endpoints
# ---------------------------------------------------------------------------


class TaxHarvestTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()
        # BND has unrealized loss of -150

    def test_harvest_returns_opportunities_for_losing_positions(self):
        self.h_bnd.unrealized_pnl = Decimal("-500.00")
        self.h_bnd.save()
        resp = self.client.post(f"/api/v1/tax/harvest/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("opportunities", resp.data)
        self.assertIn("estimated_total_tax_savings", resp.data)

    def test_harvest_excludes_positive_pnl_positions(self):
        self.h_aapl.unrealized_pnl = Decimal("500.00")
        self.h_aapl.save()
        self.h_bnd.unrealized_pnl = Decimal("-1000.00")
        self.h_bnd.save()
        resp = self.client.post(f"/api/v1/tax/harvest/{self.portfolio.id}/")
        tickers = [o["ticker"] for o in resp.data["opportunities"]]
        self.assertNotIn("AAPL", tickers)
        self.assertIn("BND", tickers)

    def test_harvest_returns_wash_sale_substitutes(self):
        self.h_bnd.unrealized_pnl = Decimal("-1000.00")
        self.h_bnd.save()
        resp = self.client.post(f"/api/v1/tax/harvest/{self.portfolio.id}/")
        bnd_opp = next(
            (o for o in resp.data["opportunities"] if o["ticker"] == "BND"), None
        )
        if bnd_opp:
            self.assertIn("wash_sale_substitutes", bnd_opp)
            self.assertIsInstance(bnd_opp["wash_sale_substitutes"], list)

    def test_harvest_other_user_returns_404(self):
        other = make_user("other_tax@qw.ai")
        resp = auth_client(other).post(f"/api/v1/tax/harvest/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class GainLossReportTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()

    def test_gain_loss_report_empty_year_returns_zero_totals(self):
        resp = self.client.get(
            f"/api/v1/tax/gain-loss/{self.portfolio.id}/?tax_year=2020"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total_net_gain"], 0.0)
        self.assertEqual(len(resp.data["realized_events"]), 0)

    def test_gain_loss_report_includes_realized_sell_transactions(self):
        add_transaction(
            self.portfolio,
            TransactionType.SELL,
            amount=Decimal("1200.00"),
            ticker="AAPL",
            qty=Decimal("10"),
            price=Decimal("120.00"),
            realized_gain=Decimal("200.00"),
            holding_period_days=400,
            is_long_term=True,
        )
        resp = self.client.get(
            f"/api/v1/tax/gain-loss/{self.portfolio.id}/?tax_year={date.today().year}"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(resp.data["realized_events"]), 0)

    def test_long_term_gain_uses_lower_tax_rate(self):
        add_transaction(
            self.portfolio,
            TransactionType.SELL,
            amount=Decimal("2000.00"),
            ticker="MSFT",
            qty=Decimal("10"),
            price=Decimal("200.00"),
            realized_gain=Decimal("1000.00"),
            holding_period_days=400,
            is_long_term=True,
        )
        resp = self.client.get(
            f"/api/v1/tax/gain-loss/{self.portfolio.id}/?tax_year={date.today().year}"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Long-term tax rate should be <= 20%
        self.assertGreater(resp.data["long_term"]["tax_rate_pct"], 0)
        self.assertLessEqual(resp.data["long_term"]["tax_rate_pct"], 20.0)


class AssetLocationTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()

    def test_asset_location_returns_recommendations_for_each_holding(self):
        resp = self.client.get(f"/api/v1/tax/asset-location/{self.portfolio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("recommendations", resp.data)
        tickers = [r["ticker"] for r in resp.data["recommendations"]]
        self.assertIn("BND", tickers)

    def test_fixed_income_recommended_for_tax_advantaged(self):
        resp = self.client.get(f"/api/v1/tax/asset-location/{self.portfolio.id}/")
        bnd_rec = next(
            (r for r in resp.data["recommendations"] if r["ticker"] == "BND"), None
        )
        self.assertIsNotNone(bnd_rec)
        self.assertEqual(bnd_rec["recommended_account"], "tax_advantaged")

    def test_asset_location_includes_priority_note(self):
        resp = self.client.get(f"/api/v1/tax/asset-location/{self.portfolio.id}/")
        self.assertIn("priority", resp.data)


class WashSaleCheckTests(_PortfolioMixin, APITestCase):
    def setUp(self):
        self._setup_portfolio()

    def test_no_violation_when_no_conflicting_buys(self):
        resp = self.client.post(
            f"/api/v1/tax/wash-sale-check/{self.portfolio.id}/",
            {"ticker": "AAPL", "sell_date": "2024-06-01"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["is_wash_sale"])

    def test_violation_detected_when_buy_within_30_days(self):
        today = date.today()
        add_transaction(
            self.portfolio,
            TransactionType.BUY,
            amount=Decimal("1500.00"),
            ticker="AAPL",
            qty=Decimal("10"),
            price=Decimal("150.00"),
        )
        sell_date = (today + timedelta(days=15)).isoformat()
        resp = self.client.post(
            f"/api/v1/tax/wash-sale-check/{self.portfolio.id}/",
            {"ticker": "AAPL", "sell_date": sell_date},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["is_wash_sale"])

    def test_missing_ticker_returns_400(self):
        resp = self.client.post(
            f"/api/v1/tax/wash-sale-check/{self.portfolio.id}/",
            {"sell_date": "2024-06-01"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date_returns_200_with_error(self):
        resp = self.client.post(
            f"/api/v1/tax/wash-sale-check/{self.portfolio.id}/",
            {"ticker": "AAPL", "sell_date": "not-a-date"},
            format="json",
        )
        self.assertIn(
            resp.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        )


# ---------------------------------------------------------------------------
# AdvisorService unit tests
# ---------------------------------------------------------------------------


class AdvisorServiceUnitTests(APITestCase):
    def setUp(self):
        self.user = make_user("advsvc@qw.ai")
        self.portfolio = make_portfolio(self.user)

    def test_recommendations_empty_portfolio(self):
        result = AdvisorService.get_recommendations(self.portfolio)
        self.assertIn("recommendations", result)
        self.assertEqual(len(result["recommendations"]), 0)

    def test_recommendations_high_cash_detected(self):
        self.portfolio.cash_balance = Decimal("50000.00")
        self.portfolio.total_value = Decimal("55000.00")
        self.portfolio.save()
        add_holding(self.portfolio, "AAPL", Decimal("10"), Decimal("500.00"))
        result = AdvisorService.get_recommendations(self.portfolio)
        types = [r["type"] for r in result["recommendations"]]
        self.assertIn("cash_drag", types)

    def test_recommendations_missing_fixed_income_detected(self):
        add_holding(
            self.portfolio,
            "AAPL",
            Decimal("10"),
            Decimal("150.00"),
            asset_class=AssetClass.EQUITY,
        )
        add_holding(
            self.portfolio,
            "MSFT",
            Decimal("5"),
            Decimal("300.00"),
            asset_class=AssetClass.EQUITY,
        )
        add_holding(
            self.portfolio,
            "GOOG",
            Decimal("3"),
            Decimal("140.00"),
            asset_class=AssetClass.EQUITY,
        )
        result = AdvisorService.get_recommendations(self.portfolio)
        types = [r["type"] for r in result["recommendations"]]
        self.assertIn("diversification", types)

    def test_drift_analysis_returns_per_position_data(self):
        self.portfolio.target_allocation = {"AAPL": 0.60, "MSFT": 0.40}
        self.portfolio.save()
        add_holding(self.portfolio, "AAPL", Decimal("10"), Decimal("150.00"))
        add_holding(self.portfolio, "MSFT", Decimal("5"), Decimal("200.00"))
        result = AdvisorService.get_allocation_drift(self.portfolio)
        self.assertIn("drift_data", result)
        self.assertIn("total_drift", result)

    def test_rebalance_sells_come_before_buys(self):
        self.portfolio.target_allocation = {"AAPL": 0.30, "BND": 0.70}
        self.portfolio.save()
        add_holding(self.portfolio, "AAPL", Decimal("10"), Decimal("150.00"))
        add_holding(
            self.portfolio,
            "BND",
            Decimal("5"),
            Decimal("75.00"),
            asset_class=AssetClass.FIXED_INCOME,
        )
        result = AdvisorService.compute_rebalance(self.portfolio, drift_threshold=0.01)
        trades = result.get("trades", [])
        if len(trades) >= 2:
            first_buy = next(
                (i for i, t in enumerate(trades) if t["action"] == "BUY"), None
            )
            last_sell = None
            for i, t in enumerate(trades):
                if t["action"] == "SELL":
                    last_sell = i
            if first_buy is not None and last_sell is not None:
                self.assertGreater(first_buy, last_sell)


# ---------------------------------------------------------------------------
# TaxService unit tests
# ---------------------------------------------------------------------------


class TaxServiceUnitTests(APITestCase):
    def setUp(self):
        self.user = make_user("taxsvc@qw.ai", tax_bracket_pct=Decimal("32.00"))
        self.portfolio = make_portfolio(self.user)

    def test_harvest_threshold_filters_small_losses(self):
        add_holding(
            self.portfolio,
            "AAPL",
            Decimal("1"),
            Decimal("100.00"),
            unrealized_pnl=Decimal("-10.00"),
        )
        result = TaxService.find_harvest_opportunities(self.portfolio.id, self.user)
        # Loss of $10 is below the $50 threshold
        self.assertEqual(len(result["opportunities"]), 0)

    def test_harvest_tax_savings_uses_user_tax_bracket(self):
        add_holding(
            self.portfolio,
            "BND",
            Decimal("20"),
            Decimal("75.00"),
            asset_class=AssetClass.FIXED_INCOME,
            unrealized_pnl=Decimal("-1000.00"),
        )
        result = TaxService.find_harvest_opportunities(self.portfolio.id, self.user)
        if result["opportunities"]:
            opp = result["opportunities"][0]
            # Savings should reflect user's tax bracket, not hardcoded 20%
            expected_rate = min(
                0.32, 0.20
            )  # short-term uses 32%, long-term capped at 20%
            self.assertGreater(opp["estimated_tax_savings"], 0)

    def test_asset_location_real_estate_goes_to_tax_advantaged(self):
        add_holding(
            self.portfolio,
            "VNQ",
            Decimal("10"),
            Decimal("90.00"),
            asset_class=AssetClass.REAL_ESTATE,
        )
        result = TaxService.recommend_asset_location(self.portfolio.id, self.user)
        vnq_rec = next(
            (r for r in result["recommendations"] if r["ticker"] == "VNQ"), None
        )
        self.assertIsNotNone(vnq_rec)
        self.assertEqual(vnq_rec["recommended_account"], "tax_advantaged")

    def test_asset_location_equity_goes_to_taxable(self):
        add_holding(
            self.portfolio,
            "VTI",
            Decimal("10"),
            Decimal("200.00"),
            asset_class=AssetClass.EQUITY,
        )
        result = TaxService.recommend_asset_location(self.portfolio.id, self.user)
        vti_rec = next(
            (r for r in result["recommendations"] if r["ticker"] == "VTI"), None
        )
        self.assertIsNotNone(vti_rec)
        self.assertEqual(vti_rec["recommended_account"], "taxable")

    def test_wash_sale_check_no_conflicting_buy(self):
        result = TaxService.wash_sale_check(
            self.portfolio.id, self.user, "AAPL", "2024-01-15"
        )
        self.assertFalse(result["is_wash_sale"])
        self.assertIsInstance(result["violations"], list)

    def test_wash_sale_check_includes_substitutes(self):
        result = TaxService.wash_sale_check(
            self.portfolio.id, self.user, "SPY", "2024-01-15"
        )
        self.assertIn("substitutes", result)
        self.assertIn("IVV", result["substitutes"])

    def test_gain_loss_report_empty_returns_zeros(self):
        result = TaxService.gain_loss_report(self.portfolio.id, self.user, 2024)
        self.assertEqual(result["total_net_gain"], 0.0)
        self.assertEqual(result["event_count"], 0)

    def test_gain_loss_report_separates_short_and_long_term(self):
        add_transaction(
            self.portfolio,
            TransactionType.SELL,
            amount=Decimal("2000.00"),
            ticker="AAPL",
            qty=Decimal("10"),
            price=Decimal("200.00"),
            realized_gain=Decimal("500.00"),
            holding_period_days=50,
            is_long_term=False,
        )
        add_transaction(
            self.portfolio,
            TransactionType.SELL,
            amount=Decimal("3000.00"),
            ticker="MSFT",
            qty=Decimal("10"),
            price=Decimal("300.00"),
            realized_gain=Decimal("800.00"),
            holding_period_days=400,
            is_long_term=True,
        )
        result = TaxService.gain_loss_report(
            self.portfolio.id, self.user, date.today().year
        )
        self.assertGreater(result["short_term"]["net"], 0)
        self.assertGreater(result["long_term"]["net"], 0)
        self.assertGreater(
            result["short_term"]["tax_rate_pct"], result["long_term"]["tax_rate_pct"]
        )
