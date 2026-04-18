from django.contrib import admin

from .models import FinancialGoal, Holding, Portfolio, Transaction


class HoldingInline(admin.TabularInline):
    model = Holding
    extra = 0
    readonly_fields = ("market_value", "unrealized_pnl", "weight", "updated_at")


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ("executed_at",)
    max_num = 20


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "total_value",
        "cash_balance",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "user__email")
    readonly_fields = ("id", "total_value", "created_at", "updated_at")
    inlines = [HoldingInline, TransactionInline]


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = (
        "ticker",
        "portfolio",
        "quantity",
        "current_price",
        "market_value",
        "unrealized_pnl",
    )
    search_fields = ("ticker", "portfolio__name")
    list_filter = ("asset_class",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("portfolio", "ticker", "transaction_type", "amount", "executed_at")
    list_filter = ("transaction_type",)
    search_fields = ("ticker", "portfolio__name")


@admin.register(FinancialGoal)
class FinancialGoalAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "goal_type",
        "target_amount",
        "current_amount",
        "is_achieved",
    )
    list_filter = ("goal_type", "is_achieved")
    search_fields = ("name", "user__email")
