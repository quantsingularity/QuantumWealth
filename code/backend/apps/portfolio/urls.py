from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FinancialGoalViewSet, PortfolioViewSet

router = DefaultRouter()
router.register("goals", FinancialGoalViewSet, basename="goals")
router.register("", PortfolioViewSet, basename="portfolio")

urlpatterns = [path("", include(router.urls))]
