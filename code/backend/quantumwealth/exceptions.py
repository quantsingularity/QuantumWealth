"""Custom DRF exception handler for consistent error envelope."""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps")


def custom_exception_handler(exc, context):
    """Wrap all errors in {error, detail, code} envelope."""
    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            "error": True,
            "code": response.status_code,
            "detail": response.data,
        }
        response.data = error_payload
    else:
        logger.exception("Unhandled exception in %s", context.get("view"))
        response = Response(
            {"error": True, "code": 500, "detail": "Internal server error."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return response
