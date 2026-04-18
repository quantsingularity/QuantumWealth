"""
Test settings for QuantumWealth.

Overrides base settings so the full test suite runs with zero external
dependencies (no PostgreSQL, no Redis, no Celery broker, no .env file).

Loaded by conftest.py via:
    os.environ["DJANGO_SETTINGS_MODULE"] = "quantumwealth.settings.test"
    django.setup()
"""

from pathlib import Path

# ─── Minimal base (replicate only what we need, avoid decouple reading .env) ─
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = "test-only-secret-key-not-for-production-abc123xyz"
DEBUG = True
ALLOWED_HOSTS = ["*"]

# ─── Applications ─────────────────────────────────────────────────────────────
# Exclude django.contrib.postgres (requires psycopg / PostgreSQL backend)
# Exclude django_celery_beat / django_celery_results (need extra DB tables)
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # Local apps
    "apps.accounts",
    "apps.portfolio",
    "apps.market",
    "apps.risk",
    "apps.advisor",
    "apps.tax",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "quantumwealth.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "quantumwealth.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "quantumwealth.wsgi.application"

# ─── Database: SQLite in-memory (zero setup) ─────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Custom user model ────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"

# ─── Cache: local memory (no Redis) ──────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "quantumwealth-test",
    }
}

# ─── Email: capture in mail.outbox ───────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@quantumwealth.ai"

# ─── Password hashing: fastest for tests ─────────────────────────────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    # Keep minimum length so tests that assert weak passwords are rejected still pass
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── JWT ─────────────────────────────────────────────────────────────────────
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.CustomTokenObtainPairSerializer",
}

# ─── REST Framework ───────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "quantumwealth.pagination.StandardPagination",
    "PAGE_SIZE": 50,
    # No throttling in tests
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/minute",
        "user": "10000/minute",
        "ai_heavy": "10000/minute",
        "market": "10000/minute",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "quantumwealth.exceptions.custom_exception_handler",
}

# ─── DRF Spectacular ──────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "QuantumWealth API",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ─── Static / Media ───────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = "/tmp/qw_test_static"
MEDIA_URL = "/media/"
MEDIA_ROOT = "/tmp/qw_test_media"

# ─── Internationalisation ─────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ─── Logging: silence everything ─────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"]},
}

# ─── Misc settings referenced by apps ────────────────────────────────────────
ALPHA_VANTAGE_API_KEY = "demo"
POLYGON_API_KEY = ""
FINNHUB_API_KEY = ""
OPENAI_API_KEY = ""
FRONTEND_URL = "http://localhost:3000"
REDIS_URL = "redis://localhost:6379/0"
AI_MARKET_DATA_PERIOD = "2y"
AI_MONTE_CARLO_DEFAULT_SIMS = 1000
AI_SIMULATION_SEED = 42

# ─── AI Models path ───────────────────────────────────────────────────────────
import sys as _sys

_code_dir = str(BASE_DIR.parent)  # .../code/
if _code_dir not in _sys.path:
    _sys.path.insert(0, _code_dir)

# ─── Disable migrations for all apps ─────────────────────────────────────────
# Setting a module to None tells Django to create tables directly from models
# instead of running migrations. Required when migration files don't exist yet.
MIGRATION_MODULES = {
    # Django built-ins
    "admin": "django.contrib.admin.migrations",
    "auth": "django.contrib.auth.migrations",
    "contenttypes": "django.contrib.contenttypes.migrations",
    "sessions": "django.contrib.sessions.migrations",
    # SimpleJWT blacklist (has its own migrations bundled with the package)
    "token_blacklist": "rest_framework_simplejwt.token_blacklist.migrations",
    # Local apps — no migration files yet, create tables from models directly
    "accounts": None,
    "portfolio": None,
    "market": None,
    "risk": None,
    "advisor": None,
    "tax": None,
}
