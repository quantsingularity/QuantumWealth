"""Portfolio views — CRUD, optimization, performance, goals, snapshots."""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .models import FinancialGoal, Portfolio
from .serializers import (
    FinancialGoalSerializer,
    HoldingCreateSerializer,
    HoldingSerializer,
    OptimizationRequestSerializer,
    PortfolioCreateSerializer,
    PortfolioDetailSerializer,
    PortfolioSerializer,
    PortfolioSnapshotSerializer,
    TransactionCreateSerializer,
    TransactionSerializer,
)
from .services import PortfolioService

logger = logging.getLogger("apps.portfolio")


class AIHeavyThrottle(UserRateThrottle):
    scope = "ai_heavy"


@extend_schema(tags=["portfolio"])
class PortfolioViewSet(viewsets.ModelViewSet):
    """Full CRUD + optimization + performance for portfolios."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Portfolio.objects.filter(
            user=self.request.user, is_active=True
        ).prefetch_related("holdings")

    def get_serializer_class(self):
        if self.action == "create":
            return PortfolioCreateSerializer
        if self.action == "retrieve":
            return PortfolioDetailSerializer
        return PortfolioSerializer

    def perform_create(self, serializer):
        portfolio = serializer.save(user=self.request.user)
        logger.info(
            "Portfolio created: %s by %s", portfolio.id, self.request.user.email
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # FIX: PortfolioCreateSerializer intentionally excludes id (and
        # other read-only fields) to restrict what's settable on creation,
        # but that means using it for the response too left the id out
        # entirely - the frontend navigates to /portfolios/{id} right
        # after creating one, and had nothing to navigate to.
        output = PortfolioSerializer(
            serializer.instance, context=self.get_serializer_context()
        )
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        portfolio = self.get_object()
        portfolio.is_active = False
        portfolio.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # FIX: combine GET + POST for the same url_path into ONE action each.
    # Two @action decorators with the same url_path cause DRF to register
    # only one, leaving the other method returning 405 Method Not Allowed.
    # ------------------------------------------------------------------

    @extend_schema(
        methods=["GET"],
        responses=HoldingSerializer(many=True),
        summary="List all holdings for a portfolio",
    )
    @extend_schema(
        methods=["POST"],
        request=HoldingCreateSerializer,
        responses=HoldingSerializer,
        summary="Add or merge a holding (weighted-average cost)",
    )
    @action(detail=True, methods=["get", "post"], url_path="holdings")
    def holdings(self, request, pk=None):
        """GET → list all holdings.  POST → add / merge a holding."""
        portfolio = self.get_object()

        if request.method == "GET":
            return Response(HoldingSerializer(portfolio.holdings.all(), many=True).data)

        # POST
        ser = HoldingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        holding = PortfolioService.upsert_holding(
            portfolio=portfolio,
            ticker=d["ticker"],
            quantity=d["quantity"],
            average_cost=d["average_cost"],
            name=d.get("name", ""),
            asset_class=d.get("asset_class", "equity"),
        )
        return Response(HoldingSerializer(holding).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        methods=["GET"],
        responses=TransactionSerializer(many=True),
        summary="List all transactions for a portfolio",
    )
    @extend_schema(
        methods=["POST"],
        request=TransactionCreateSerializer,
        responses=TransactionSerializer,
        summary="Record a buy/sell/deposit/withdrawal transaction",
    )
    @action(detail=True, methods=["get", "post"], url_path="transactions")
    def transactions(self, request, pk=None):
        """GET → list transactions (paginated, filterable by ?type=).  POST → record one."""
        portfolio = self.get_object()

        if request.method == "GET":
            txn_type = request.query_params.get("type")
            qs = portfolio.transactions.all()
            if txn_type:
                qs = qs.filter(transaction_type=txn_type)
            page = self.paginate_queryset(qs)
            if page is not None:
                return self.get_paginated_response(
                    TransactionSerializer(page, many=True).data
                )
            return Response(TransactionSerializer(qs, many=True).data)

        # POST
        ser = TransactionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        txn = PortfolioService.record_transaction(portfolio, ser.validated_data)
        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=OptimizationRequestSerializer)
    @action(
        detail=True,
        methods=["post"],
        url_path="optimize",
        throttle_classes=[AIHeavyThrottle],
    )
    def optimize(self, request, pk=None):
        """Run AI portfolio optimization (mean_variance / black_litterman / risk_parity / hrp)."""
        portfolio = self.get_object()
        ser = OptimizationRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        result = PortfolioService.optimize(
            portfolio=portfolio,
            strategy=d["strategy"],
            risk_tolerance=d["risk_tolerance"],
            target_return=d.get("target_return"),
            max_weight=d["max_weight"],
            constraints=d.get("constraints", {}),
        )
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(
        detail=True,
        methods=["get"],
        url_path="performance",
        throttle_classes=[AIHeavyThrottle],
    )
    def performance(self, request, pk=None):
        """Full risk/performance report: Sharpe, Sortino, VaR, drawdown, etc."""
        portfolio = self.get_object()
        result = PortfolioService.get_performance(portfolio)
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @extend_schema(responses=PortfolioSnapshotSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        """Daily portfolio value history for charting."""
        portfolio = self.get_object()
        days = int(request.query_params.get("days", 365))
        snapshots = portfolio.snapshots.all()[:days]
        return Response(PortfolioSnapshotSerializer(snapshots, many=True).data)

    @action(detail=True, methods=["post"], url_path="snapshot")
    def snapshot(self, request, pk=None):
        """Manually trigger a portfolio value snapshot."""
        portfolio = self.get_object()
        PortfolioService.take_snapshot(portfolio)
        return Response({"detail": "Snapshot recorded."})


@extend_schema(tags=["portfolio"])
class FinancialGoalViewSet(viewsets.ModelViewSet):
    """CRUD for financial goals."""

    serializer_class = FinancialGoalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FinancialGoal.objects.filter(user=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        url_path="plan",
        throttle_classes=[AIHeavyThrottle],
    )
    def plan(self, request, pk=None):
        """Generate an AI goal attainment plan with milestones and scenarios."""
        goal = self.get_object()
        from apps.advisor.services import AdvisorService

        result = AdvisorService.generate_goal_plan(
            goal_type=goal.goal_type,
            target_amount=float(goal.target_amount),
            current_savings=float(goal.current_amount),
            monthly_contribution=float(goal.monthly_contribution),
            target_date=goal.target_date,
            expected_return=float(goal.expected_return),
            inflation_rate=float(goal.inflation_rate),
        )
        return Response(result)
