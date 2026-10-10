# RewardGate: Containerized Sandbox Environment and Telemetry Service
FROM python:3.12-slim

# Set environment invariants
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install minimal OS dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Create dedicated unprivileged user for sandbox security boundary
RUN groupadd -r rewardgate && useradd -r -g rewardgate -d /app -s /sbin/nologin rewardgate

WORKDIR /app

# Copy dependency specifications first for layer caching
COPY pyproject.toml /app/

# Install dependencies and project in editable/production mode
COPY src/ /app/src/
RUN pip install --no-cache-dir /app

# Copy docs, examples, and assets
COPY docs/ /app/docs/
COPY examples/ /app/examples/

# Set ownership and permissions
RUN chown -R rewardgate:rewardgate /app

USER rewardgate

# Expose port for the developer telemetry dashboard
EXPOSE 8765

# Default entrypoint dispatches to the Typer CLI
ENTRYPOINT ["rewardgate"]
CMD ["--help"]
