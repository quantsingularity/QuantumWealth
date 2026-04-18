"""Development settings — debug mode, relaxed security."""

from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Show SQL queries
LOGGING["loggers"]["django.db.backends"] = {
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}

# Allow all CORS in dev
CORS_ALLOW_ALL_ORIGINS = True

# Use console email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable throttling in development
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
