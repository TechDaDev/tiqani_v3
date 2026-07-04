# =============================================================================
# tiqani_v3 — Production Dockerfile
# =============================================================================
FROM python:3.12-slim-bookworm AS builder

# Prevent Python from writing .pyc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system build deps (psycopg2, Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Runtime stage — slimmer image
# =============================================================================
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

# Runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r django && useradd -r -g django django

WORKDIR $APP_HOME

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project code
COPY . .

# Ownership for runtime
RUN chmod +x scripts/entrypoint.sh && chown -R django:django $APP_HOME

USER django

EXPOSE 8000

ENTRYPOINT ["./scripts/entrypoint.sh"]

# Default command — overridden by entrypoint in compose
CMD ["gunicorn", "tiqani_v3.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
