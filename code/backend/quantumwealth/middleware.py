"""Request logging middleware."""

import logging
import time
import uuid

logger = logging.getLogger("apps")


class RequestLoggingMiddleware:
    """Logs every request with duration, status code and request ID."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id
        start = time.monotonic()

        response = self.get_response(request)

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        logger.info(
            "HTTP %s %s → %s [%sms] rid=%s",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        response["X-Request-ID"] = request_id
        return response
