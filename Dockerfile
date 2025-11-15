# Multi-Stage Build Dockerfile for FastAPI Frame.io Webhook Receiver
# Optimized for GCP Cloud Run deployment

# Stage 1: Builder - Install dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime - Create minimal production image
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser app/ app/

# Switch to non-root user
USER appuser

# Add user site-packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Set Python to run in unbuffered mode (important for logging in Cloud Run)
ENV PYTHONUNBUFFERED=1

# Expose port (Cloud Run will inject PORT env var, default to 8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run the application using module syntax for proper imports
CMD ["python", "-m", "app.main"]
