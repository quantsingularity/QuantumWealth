from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Notification, PriceAlert, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "full_name",
        "risk_profile",
        "risk_score",
        "is_verified",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "is_verified", "is_staff", "risk_profile", "country")
    search_fields = ("email", "full_name", "phone_number")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login")
    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            "Personal",
            {
                "fields": (
                    "full_name",
                    "phone_number",
                    "date_of_birth",
                    "country",
                    "currency",
                )
            },
        ),
        (
            "Risk Profile",
            {
                "fields": (
                    "risk_profile",
                    "risk_score",
                    "investment_horizon_years",
                    "tax_bracket_pct",
                )
            },
        ),
        ("Financial", {"fields": ("annual_income", "net_worth")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Notifications",
            {
                "fields": (
                    "notify_price_alerts",
                    "notify_rebalance",
                    "notify_weekly_digest",
                    "notify_tax_opportunities",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_login")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password1", "password2"),
            },
        ),
    )


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "ticker",
        "alert_type",
        "threshold",
        "is_active",
        "triggered_at",
    )
    list_filter = ("alert_type", "is_active")
    search_fields = ("user__email", "ticker")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "title", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("user__email", "title")
