# ============================================================
# Stage 1 — Dependency Builder
# ============================================================
# Use a full-fat Python slim image so we have the build tools
# needed by binary wheels (psycopg2-binary, bcrypt, cryptography).
FROM python:3.11-slim AS builder

# Prevent .pyc files and ensure unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install OS-level build deps for psycopg2-binary, cryptography, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtual environment so we can copy it cleanly
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip inside the venv first
RUN pip install --upgrade pip

# Copy only the dependency manifest — layer-cache friendly
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ============================================================
# Stage 2 — Production Runtime
# ============================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install Tini for proper PID 1 / signal handling & libpq runtime only
RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create a dedicated non-root user (security best-practice)
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --no-create-home --shell /bin/false appuser

# Copy application source
COPY --chown=appuser:appgroup . .

# Drop privileges
USER appuser

EXPOSE 8000

# Number of Uvicorn worker processes — override via env var in production
# (formula: (2 x CPU cores) + 1 is the Gunicorn recommendation)
ENV UVICORN_WORKERS=2

# Tini as PID 1 ensures SIGTERM is forwarded cleanly to Uvicorn
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS} --loop uvloop --http httptools --no-access-log"]
