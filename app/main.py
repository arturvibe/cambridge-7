"""
FastAPI application for receiving Frame.io webhooks.

This module wires dependencies and configures the application.
Business logic is in app/core, infrastructure in app/infrastructure.
"""

import logging
import os
from datetime import UTC, datetime
from functools import lru_cache

# Configure logging FIRST, before other local imports
from app.logging_config import setup_global_logging

setup_global_logging()

# Now import other modules (they will use the configured logging)
from fastapi import Depends, FastAPI  # noqa: E402

from app.api import frameio  # noqa: E402
from app.api.frameio import get_webhook_service_dependency  # noqa: E402
from app.core.services import WebhookService  # noqa: E402
from app.infrastructure.pubsub_publisher import GooglePubSubPublisher  # noqa: E402

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Frame.io Webhook Receiver",
    description="Receives and logs Frame.io V4 webhooks",
    version="1.0.0",
)


# ============================================================================
# Dependency Injection Configuration (Wiring)
# ============================================================================


@lru_cache()
def get_event_publisher() -> GooglePubSubPublisher:
    """
    Provide the event publisher dependency.

    Uses lru_cache for singleton behavior - same instance across requests.
    """
    return GooglePubSubPublisher()


def get_webhook_service(
    event_publisher: GooglePubSubPublisher = Depends(get_event_publisher),
) -> WebhookService:
    """
    Provide the webhook service dependency.

    This is where we wire the core service with its infrastructure dependencies.
    """
    return WebhookService(event_publisher=event_publisher)


# Override the dependency in the router to use our wired service
app.dependency_overrides[get_webhook_service_dependency] = get_webhook_service


# ============================================================================
# Application Lifecycle
# ============================================================================


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down application...")
    try:
        # Close the event publisher
        get_event_publisher().close()
    except Exception as e:
        # Gracefully handle shutdown errors (e.g., client not initialized)
        logger.warning(f"Error closing event publisher during shutdown: {e}")


# ============================================================================
# Health Check Endpoints
# ============================================================================


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "cambridge",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy"}


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(frameio.router)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
