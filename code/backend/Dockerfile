FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    gcc \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Pre-create the directories that get mounted as named volumes
# (staticfiles, media) so Docker copies their ownership into the volume on
# first creation. Without this, a fresh named volume mounted at a path that
# doesn't already exist in the image defaults to root ownership, and
# collectstatic would fail with a permission error under the non-root user
# below on every container startup.
RUN mkdir -p /app/staticfiles /app/media

# Non-root user for security
RUN useradd -m -u 1000 appuser \
 && chown -R appuser:appuser /app
USER appuser

# Runtime settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=quantumwealth.settings.production

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/api/schema/ || exit 1
