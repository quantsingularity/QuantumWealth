"""Risk engine views."""

import logging

from ai_models.risk_engine import RiskEngine
from apps.portfolio.models import Portfolio
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

logger = logging.getLogger("apps.risk")


class AIHeavyThrottle(UserRateThrottle):
    scope = "ai_heavy"


def _get_portfolio(portfolio_id, user):
    from django.shortcuts import get_object_or_404

    return get_object_or_404(Portfolio, id=portfolio_id, user=user, is_active=True)


def _tickers_weights_value(portfolio):
    holdings = list(portfolio.holdings.all())
    tickers = [h.ticker for h in holdings]
    weights = [float(h.weight) for h in holdings]
    total_value = float(portfolio.total_value)
    return tickers, weights, total_value


@extend_schema(tags=["risk"])
class RiskReportView(APIView):
    """Full risk report: Sharpe, Sortino, VaR, CVaR, drawdown, stress tests."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIHeavyThrottle]

    def get(self, request, portfolio_id):
        portfolio = _get_portfolio(portfolio_id, request.user)
        tickers, weights, total_value = _tickers_weights_value(portfolio)
        if not tickers:
            return Response({"error": "Portfolio has no holdings."}, status=400)
        engine = RiskEngine()
        return Response(engine.full_report(tickers, weights, total_value))


@extend_schema(tags=["risk"])
class VaRView(APIView):
    """Compute Value at Risk and Conditional VaR."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIHeavyThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "confidence",
                OpenApiTypes.FLOAT,
                description="Confidence level (0.90–0.99)",
            ),
            OpenApiParameter(
                "horizon_days", OpenApiTypes.INT, description="Time horizon in days"
            ),
            OpenApiParameter(
                "method", OpenApiTypes.STR, description="historical or parametric"
            ),
        ]
    )
    def get(self, request, portfolio_id):
        portfolio = _get_portfolio(portfolio_id, request.user)
        tickers, weights, total_value = _tickers_weights_value(portfolio)
        if not tickers:
            return Response({"error": "Portfolio has no holdings."}, status=400)
        confidence = float(request.query_params.get("confidence", 0.95))
        horizon_days = int(request.query_params.get("horizon_days", 1))
        method = request.query_params.get("method", "historical")
        engine = RiskEngine()
        return Response(
            engine.compute_var(
                tickers, weights, total_value, confidence, horizon_days, method
            )
        )


@extend_schema(tags=["risk"])
class StressTestView(APIView):
    """Run historical stress scenarios."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIHeavyThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "scenario",
                OpenApiTypes.STR,
                description="2008_crisis, covid_crash, dot_com_bust, rate_shock, all",
            ),
        ]
    )
    def post(self, request, portfolio_id):
        portfolio = _get_portfolio(portfolio_id, request.user)
        tickers, weights, total_value = _tickers_weights_value(portfolio)
        if not tickers:
            return Response({"error": "Portfolio has no holdings."}, status=400)
        scenario = request.data.get("scenario", "2008_crisis")
        engine = RiskEngine()
        if scenario == "all":
            results = {}
            for s in ["2008_crisis", "covid_crash", "dot_com_bust", "rate_shock"]:
                results[s] = engine.stress_test(tickers, weights, total_value, s)
            return Response(results)
        return Response(engine.stress_test(tickers, weights, total_value, scenario))


@extend_schema(tags=["risk"])
class MonteCarloView(APIView):
    """Run Monte Carlo simulation for portfolio projection."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIHeavyThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "simulations",
                OpenApiTypes.INT,
                description="Number of simulations (1000–50000)",
            ),
            OpenApiParameter(
                "horizon_years",
                OpenApiTypes.INT,
                description="Projection horizon in years",
            ),
        ]
    )
    def get(self, request, portfolio_id):
        portfolio = _get_portfolio(portfolio_id, request.user)
        tickers, weights, total_value = _tickers_weights_value(portfolio)
        if not tickers:
            return Response({"error": "Portfolio has no holdings."}, status=400)
        simulations = min(int(request.query_params.get("simulations", 10000)), 50000)
        horizon_years = int(request.query_params.get("horizon_years", 10))
        engine = RiskEngine()
        return Response(
            engine.monte_carlo(
                tickers, weights, total_value, simulations, horizon_years
            )
        )


@extend_schema(tags=["risk"])
class CorrelationMatrixView(APIView):
    """Return correlation matrix for portfolio holdings."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, portfolio_id):
        portfolio = _get_portfolio(portfolio_id, request.user)
        tickers = list(portfolio.holdings.values_list("ticker", flat=True))
        if len(tickers) < 2:
            return Response(
                {"error": "Need at least 2 holdings for correlation."}, status=400
            )
        engine = RiskEngine()
        return Response(engine.correlation_matrix(tickers))
