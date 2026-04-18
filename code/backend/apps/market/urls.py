from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BulkQuoteView,
    HistoryView,
    PredictView,
    QuoteView,
    SearchView,
    SectorPerformanceView,
    WatchlistViewSet,
)

router = DefaultRouter()
router.register("watchlists", WatchlistViewSet, basename="watchlists")

urlpatterns = [
    path("quote/<str:ticker>/", QuoteView.as_view(), name="market-quote"),
    path("quotes/bulk/", BulkQuoteView.as_view(), name="market-quotes-bulk"),
    path("history/<str:ticker>/", HistoryView.as_view(), name="market-history"),
    path("predict/<str:ticker>/", PredictView.as_view(), name="market-predict"),
    path("search/", SearchView.as_view(), name="market-search"),
    path("sectors/", SectorPerformanceView.as_view(), name="market-sectors"),
    path("", include(router.urls)),
]
