from django.urls import path

from .views import (
    DriftView,
    GoalPlanView,
    RebalanceView,
    RecommendationsView,
    SuggestedAllocationView,
)

urlpatterns = [
    path("plan/", GoalPlanView.as_view(), name="advisor-plan"),
    path(
        "rebalance/<uuid:portfolio_id>/",
        RebalanceView.as_view(),
        name="advisor-rebalance",
    ),
    path(
        "recommendations/<uuid:portfolio_id>/",
        RecommendationsView.as_view(),
        name="advisor-recommendations",
    ),
    path("drift/<uuid:portfolio_id>/", DriftView.as_view(), name="advisor-drift"),
    path(
        "suggested-allocation/",
        SuggestedAllocationView.as_view(),
        name="advisor-suggested-allocation",
    ),
]
