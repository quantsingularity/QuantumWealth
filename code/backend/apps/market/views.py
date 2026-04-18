"""Market views."""

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .models import Watchlist
from .services import MarketService

logger = logging.getLogger("apps.market")


class MarketThrottle(UserRateThrottle):
    scope = "market"


class AIHeavyThrottle(UserRateThrottle):
    scope = "ai_heavy"


@extend_schema(tags=["market"])
class QuoteView(APIView):
    """Get real-time quote for a single ticker."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [MarketThrottle]

    def get(self, request, ticker):
        result = MarketService.get_quote(ticker.upper())
        return Response(result)


@extend_schema(tags=["market"])
class BulkQuoteView(APIView):
    """Get quotes for multiple tickers at once."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [MarketThrottle]

    def post(self, request):
        tickers = request.data.get("tickers", [])
        if not tickers or not isinstance(tickers, list):
            return Response({"error": "Provide a list of tickers."}, status=400)
        tickers = [t.upper() for t in tickers[:50]]  # cap at 50
        results = MarketService.get_quotes_bulk(tickers)
        return Response(results)


@extend_schema(tags=["market"])
class HistoryView(APIView):
    """Get historical OHLCV data."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [MarketThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "period", OpenApiTypes.STR, description="1d,5d,1mo,3mo,6mo,1y,2y,5y,max"
            ),
            OpenApiParameter(
                "interval", OpenApiTypes.STR, description="1m,5m,15m,1h,1d,1wk,1mo"
            ),
        ]
    )
    def get(self, request, ticker):
        period = request.query_params.get("period", "1y")
        interval = request.query_params.get("interval", "1d")
        result = MarketService.get_history(ticker.upper(), period, interval)
        return Response(result)


@extend_schema(tags=["market"])
class PredictView(APIView):
    """AI price prediction for a ticker."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIHeavyThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "horizon_days", OpenApiTypes.INT, description="Forecast horizon in days"
            ),
        ]
    )
    def get(self, request, ticker):
        horizon_days = int(request.query_params.get("horizon_days", 30))
        result = MarketService.predict(ticker.upper(), horizon_days)
        return Response(result)


@extend_schema(tags=["market"])
class SearchView(APIView):
    """Search for securities by name or ticker."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        q = request.query_params.get("q", "")
        if not q:
            return Response({"error": "Provide a search query via ?q="}, status=400)
        results = MarketService.search(q)
        return Response(results)


@extend_schema(tags=["market"])
class SectorPerformanceView(APIView):
    """Get YTD performance for all S&P 500 sectors."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(MarketService.get_sector_performance())


@extend_schema(tags=["market"])
class WatchlistViewSet(viewsets.ModelViewSet):
    """CRUD for user watchlists."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        from rest_framework import serializers

        class WatchlistSerializer(serializers.ModelSerializer):
            class Meta:
                model = Watchlist
                fields = ["id", "name", "tickers", "created_at", "updated_at"]
                read_only_fields = ["id", "created_at", "updated_at"]

        return WatchlistSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get"], url_path="quotes")
    def quotes(self, request, pk=None):
        """Get live quotes for all tickers in this watchlist."""
        watchlist = self.get_object()
        if not watchlist.tickers:
            return Response([])
        results = MarketService.get_quotes_bulk(watchlist.tickers)
        return Response(list(results.values()))
