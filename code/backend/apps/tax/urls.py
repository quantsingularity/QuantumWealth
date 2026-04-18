from django.urls import path

from .views import (
    AssetLocationView,
    GainLossReportView,
    TaxHarvestView,
    WashSaleCheckView,
)

urlpatterns = [
    path("harvest/<uuid:portfolio_id>/", TaxHarvestView.as_view(), name="tax-harvest"),
    path(
        "gain-loss/<uuid:portfolio_id>/",
        GainLossReportView.as_view(),
        name="tax-gain-loss",
    ),
    path(
        "asset-location/<uuid:portfolio_id>/",
        AssetLocationView.as_view(),
        name="tax-asset-location",
    ),
    path(
        "wash-sale-check/<uuid:portfolio_id>/",
        WashSaleCheckView.as_view(),
        name="tax-wash-sale-check",
    ),
]
