"""QuantumWealth URL Configuration."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# Admin customization
admin.site.site_header = "QuantumWealth Administration"
admin.site.site_title = "QuantumWealth Admin"
admin.site.index_title = "Platform Management"

api_v1_patterns = [
    path("auth/", include("apps.accounts.urls")),
    path("portfolio/", include("apps.portfolio.urls")),
    path("market/", include("apps.market.urls")),
    path("risk/", include("apps.risk.urls")),
    path("advisor/", include("apps.advisor.urls")),
    path("tax/", include("apps.tax.urls")),
]

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/", include(api_v1_patterns)),
    # OpenAPI schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
