"""Tax optimization views."""

import logging
from datetime import datetime

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import TaxService

logger = logging.getLogger("apps.tax")


@extend_schema(tags=["tax"])
class TaxHarvestView(APIView):
    """Identify tax-loss harvesting opportunities with wash-sale compliant substitutes."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, portfolio_id):
        result = TaxService.find_harvest_opportunities(portfolio_id, request.user)
        return Response(result)


@extend_schema(tags=["tax"])
class GainLossReportView(APIView):
    """Realized gain/loss report with short- vs long-term breakdown and tax estimates."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "tax_year", OpenApiTypes.INT, description="Tax year (e.g. 2024)"
            ),
        ]
    )
    def get(self, request, portfolio_id):
        tax_year = int(request.query_params.get("tax_year", datetime.now().year))
        result = TaxService.gain_loss_report(portfolio_id, request.user, tax_year)
        return Response(result)


@extend_schema(tags=["tax"])
class AssetLocationView(APIView):
    """Recommend optimal asset placement across taxable vs tax-advantaged accounts."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, portfolio_id):
        result = TaxService.recommend_asset_location(portfolio_id, request.user)
        return Response(result)


@extend_schema(tags=["tax"])
class WashSaleCheckView(APIView):
    """Check whether a proposed sale would trigger a wash-sale violation."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, portfolio_id):
        ticker = request.data.get("ticker", "")
        sell_date = request.data.get("sell_date", "")
        if not ticker or not sell_date:
            return Response(
                {"error": "Provide ticker and sell_date (YYYY-MM-DD)."}, status=400
            )
        result = TaxService.wash_sale_check(
            portfolio_id, request.user, ticker, sell_date
        )
        return Response(result)
