"""Production settings — hardened security, real email, etc."""

from .base import *  # noqa

DEBUG = False

# ─── Security headers ─────────────────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# ─── Email (Anymail / real SMTP) ──────────────────────────────────────────────
from decouple import config

EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)

# ─── Logging — JSON format in production ──────────────────────────────────────
LOGGING["handlers"]["console"]["formatter"] = "json"
