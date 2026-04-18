"""Portfolio serializers."""

from decimal import Decimal

from rest_framework import serializers

from .models import (
    AssetClass,
    FinancialGoal,
    Holding,
    Portfolio,
    PortfolioSnapshot,
    Transaction,
    TransactionType,
)


class HoldingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Holding
        fields = [
            "id",
            "ticker",
            "name",
            "asset_class",
            "quantity",
            "average_cost",
            "current_price",
            "market_value",
            "unrealized_pnl",
            "unrealized_pnl_pct",
            "weight",
            "day_change",
            "day_change_pct",
            "price_updated_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "market_value",
            "unrealized_pnl",
            "unrealized_pnl_pct",
            "weight",
            "day_change",
            "day_change_pct",
            "price_updated_at",
            "updated_at",
        ]


class HoldingCreateSerializer(serializers.Serializer):
    ticker = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=255, required=False, default="")
    asset_class = serializers.ChoiceField(
        choices=AssetClass.choices, default=AssetClass.EQUITY
    )
    quantity = serializers.DecimalField(
        max_digits=18, decimal_places=6, min_value=Decimal("0.000001")
    )
    average_cost = serializers.DecimalField(
        max_digits=18, decimal_places=4, min_value=Decimal("0")
    )

    def validate_ticker(self, value):
        return value.upper().strip()


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "ticker",
            "transaction_type",
            "quantity",
            "price",
            "amount",
            "fees",
            "notes",
            "executed_at",
            "realized_gain",
            "holding_period_days",
            "is_long_term",
        ]
        read_only_fields = [
            "id",
            "executed_at",
            "realized_gain",
            "holding_period_days",
            "is_long_term",
        ]


class TransactionCreateSerializer(serializers.Serializer):
    ticker = serializers.CharField(max_length=20, required=False, allow_blank=True)
    transaction_type = serializers.ChoiceField(choices=TransactionType.choices)
    quantity = serializers.DecimalField(
        max_digits=18, decimal_places=6, required=False, allow_null=True
    )
    price = serializers.DecimalField(
        max_digits=18, decimal_places=4, required=False, allow_null=True
    )
    amount = serializers.DecimalField(max_digits=18, decimal_places=4)
    fees = serializers.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0")
    )
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class PortfolioSerializer(serializers.ModelSerializer):
    unrealized_pnl = serializers.SerializerMethodField()
    holdings_count = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = [
            "id",
            "name",
            "description",
            "cash_balance",
            "total_value",
            "is_active",
            "target_allocation",
            "benchmark_ticker",
            "unrealized_pnl",
            "holdings_count",
            "annualized_return",
            "sharpe_ratio",
            "max_drawdown",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_value",
            "annualized_return",
            "sharpe_ratio",
            "max_drawdown",
            "created_at",
            "updated_at",
        ]

    def get_unrealized_pnl(self, obj):
        return float(
            sum(
                (h.current_price - h.average_cost) * h.quantity
                for h in obj.holdings.all()
            )
        )

    def get_holdings_count(self, obj):
        return obj.holdings.count()


class PortfolioCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = [
            "name",
            "description",
            "cash_balance",
            "target_allocation",
            "benchmark_ticker",
        ]


class PortfolioDetailSerializer(PortfolioSerializer):
    holdings = HoldingSerializer(many=True, read_only=True)
    recent_transactions = serializers.SerializerMethodField()

    class Meta(PortfolioSerializer.Meta):
        fields = PortfolioSerializer.Meta.fields + ["holdings", "recent_transactions"]

    def get_recent_transactions(self, obj):
        txns = obj.transactions.order_by("-executed_at")[:10]
        return TransactionSerializer(txns, many=True).data


class OptimizationRequestSerializer(serializers.Serializer):
    strategy = serializers.ChoiceField(
        choices=["mean_variance", "black_litterman", "risk_parity", "hrp"],
        default="mean_variance",
    )
    risk_tolerance = serializers.FloatField(min_value=0.0, max_value=1.0, default=0.5)
    target_return = serializers.FloatField(required=False, allow_null=True)
    max_weight = serializers.FloatField(min_value=0.05, max_value=1.0, default=0.40)
    constraints = serializers.DictField(required=False, default=dict)


class OptimizationResultSerializer(serializers.Serializer):
    strategy = serializers.CharField()
    expected_return = serializers.FloatField()
    expected_volatility = serializers.FloatField()
    sharpe_ratio = serializers.FloatField()
    allocations = serializers.ListField()
    efficient_frontier = serializers.ListField()
    metadata = serializers.DictField()


class FinancialGoalSerializer(serializers.ModelSerializer):
    progress_pct = serializers.SerializerMethodField()

    class Meta:
        model = FinancialGoal
        fields = [
            "id",
            "name",
            "goal_type",
            "target_amount",
            "current_amount",
            "monthly_contribution",
            "target_date",
            "expected_return",
            "inflation_rate",
            "is_achieved",
            "achieved_at",
            "priority",
            "notes",
            "progress_pct",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_achieved",
            "achieved_at",
            "created_at",
            "updated_at",
        ]

    def get_progress_pct(self, obj):
        return obj.progress_pct

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class PortfolioSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioSnapshot
        fields = [
            "date",
            "total_value",
            "cash_balance",
            "holdings_value",
            "daily_return_pct",
        ]
