"""Advisor views — goal planning, rebalancing, recommendations, drift analysis."""

import logging

from apps.portfolio.models import Portfolio
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .services import AdvisorService

logger = logging.getLogger("apps.advisor")


def _get_portfolio(portfolio_id, user):
    from django.shortcuts import get_object_or_404

    return get_object_or_404(Portfolio, id=portfolio_id, user=user, is_active=True)


class AIHeavyThrottle(UserRateThrottle):
    scope = "ai_heavy"


@extend_schema(tags=["advisor"])
class GoalPlanView(APIView):
    """Generate an AI-powered financial plan for a goal."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIHeavyThrottle]

    def post(self, request):
        data = request.data
        required = [
            "goal_type",
            "target_amount",
            "current_savings",
            "monthly_contribution",
            "target_date",
        ]
        missing = [f for f in required if f not in data]
        if missing:
            return Response({"error": f"Missing fields: {missing}"}, status=400)

        from datetime import datetime

        try:
            target_date = datetime.fromisoformat(data["target_date"])
        except ValueError:
            return Response(
                {"error": "Invalid target_date. Use ISO 8601 format."}, status=400
            )

        result = AdvisorService.generate_goal_plan(
            goal_type=data["goal_type"],
            target_amount=float(data["target_amount"]),
            current_savings=float(data["current_savings"]),
            monthly_contribution=float(data["monthly_contribution"]),
            target_date=target_date,
            expected_return=float(data.get("expected_return", 0.075)),
            inflation_rate=float(data.get("inflation_rate", 0.03)),
            inflation_adjusted=bool(data.get("inflation_adjusted", True)),
        )
        return Response(result)


@extend_schema(tags=["advisor"])
class RebalanceView(APIView):
    """Compute rebalancing trades for a portfolio."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIHeavyThrottle]

    def post(self, request, portfolio_id):
        portfolio = _get_portfolio(portfolio_id, request.user)
        method = request.data.get("method", "threshold")
        drift_threshold = float(request.data.get("drift_threshold", 0.05))
        min_trade_value = float(request.data.get("min_trade_value", 100.0))

        result = AdvisorService.compute_rebalance(
            portfolio=portfolio,
            method=method,
            drift_threshold=drift_threshold,
            min_trade_value=min_trade_value,
        )
        return Response(result)


@extend_schema(tags=["advisor"])
class RecommendationsView(APIView):
    """Get AI-generated actionable recommendations for a portfolio."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, portfolio_id):
        portfolio = _get_portfolio(portfolio_id, request.user)
        result = AdvisorService.get_recommendations(portfolio)
        return Response(result)


@extend_schema(tags=["advisor"])
class DriftView(APIView):
    """Get current allocation drift vs target for a portfolio."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, portfolio_id):
        portfolio = _get_portfolio(portfolio_id, request.user)
        result = AdvisorService.get_allocation_drift(portfolio)
        return Response(result)


@extend_schema(tags=["advisor"])
class SuggestedAllocationView(APIView):
    """Return suggested portfolio allocation based on user risk profile."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.accounts.views import PROFILE_ALLOCATIONS

        profile = request.user.risk_profile
        allocation = PROFILE_ALLOCATIONS.get(profile, PROFILE_ALLOCATIONS["moderate"])

        RISK_RETURN_MAP = {
            "conservative": {"mu": 0.045, "sigma": 0.060},
            "moderate_conservative": {"mu": 0.060, "sigma": 0.090},
            "moderate": {"mu": 0.075, "sigma": 0.120},
            "moderate_aggressive": {"mu": 0.090, "sigma": 0.150},
            "aggressive": {"mu": 0.110, "sigma": 0.190},
        }
        stats = RISK_RETURN_MAP.get(profile, RISK_RETURN_MAP["moderate"])

        return Response(
            {
                "risk_profile": profile,
                "risk_score": request.user.risk_score,
                "suggested_allocation": allocation,
                "expected_annual_return": stats["mu"],
                "expected_volatility": stats["sigma"],
                "description": f"Based on your {profile.replace('_', ' ')} risk profile.",
            }
        )
