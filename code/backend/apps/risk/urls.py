from django.urls import path

from .views import (
    CorrelationMatrixView,
    MonteCarloView,
    RiskReportView,
    StressTestView,
    VaRView,
)

urlpatterns = [
    path("report/<uuid:portfolio_id>/", RiskReportView.as_view(), name="risk-report"),
    path("var/<uuid:portfolio_id>/", VaRView.as_view(), name="risk-var"),
    path(
        "stress-test/<uuid:portfolio_id>/",
        StressTestView.as_view(),
        name="risk-stress-test",
    ),
    path(
        "monte-carlo/<uuid:portfolio_id>/",
        MonteCarloView.as_view(),
        name="risk-monte-carlo",
    ),
    path(
        "correlation/<uuid:portfolio_id>/",
        CorrelationMatrixView.as_view(),
        name="risk-correlation",
    ),
]
