# BOA - Bayesian Optimization Assistant
# Multi-stage Docker build

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY pyproject.toml ./
COPY src/ ./src/

# Install package
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[server]"


# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.13-slim AS runtime

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 boa && \
    useradd --uid 1000 --gid boa --shell /bin/bash --create-home boa

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /app/src ./src

# Create data directories
RUN mkdir -p /app/data /app/artifacts && \
    chown -R boa:boa /app

# Switch to non-root user
USER boa

# Environment
ENV BOA_DATABASE_URL="sqlite:////app/data/boa.db" \
    BOA_ARTIFACTS_DIR="/app/artifacts" \
    BOA_HOST="0.0.0.0" \
    BOA_PORT="8000"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${BOA_PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "-m", "uvicorn", "boa.server.app:app", "--host", "0.0.0.0", "--port", "8000"]





