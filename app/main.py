"""
FastAPI application for receiving Frame.io webhooks.

This module wires dependencies and configures the application.
Business logic is in app/core, infrastructure in app/infrastructure.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache

# Configure logging FIRST, before other local imports
from app.logging_config import setup_global_logging

setup_global_logging()

# Now import other modules (they will use the configured logging)
from fastapi import Depends, FastAPI, Request, status  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from starlette.middleware.sessions import SessionMiddleware  # noqa: E402

from app.api import frameio  # noqa: E402
from app.api import magic  # noqa: E402
from app.oauth import router as oauth_router  # noqa: E402
from app.api.frameio import get_webhook_service_dependency  # noqa: E402
from app.auth.dependencies import get_current_user  # noqa: E402
from app.core.exceptions import PublisherError  # noqa: E402
from app.core.services import FrameioWebhookService  # noqa: E402
from app.infrastructure.pubsub_publisher import GooglePubSubPublisher  # noqa: E402

logger = logging.getLogger(__name__)


# ============================================================================
# Application Lifecycle
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events using modern FastAPI pattern.
    """
    # Startup: nothing to do (dependencies are lazy-loaded)
    logger.info("Application starting up...")
    yield
    # Shutdown: cleanup resources
    logger.info("Shutting down application...")
    try:
        get_event_publisher().close()
    except Exception as e:
        # Gracefully handle shutdown errors (e.g., client not initialized)
        logger.warning(f"Error closing event publisher during shutdown: {e}")


app = FastAPI(
    title="Frame.io Webhook Receiver",
    description="Receives and logs Frame.io V4 webhooks",
    version="1.0.0",
    lifespan=lifespan,
)

# Session middleware required for OAuth2 state management (authlib)
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
if not SESSION_SECRET_KEY:
    raise ValueError("SESSION_SECRET_KEY is not set in the environment.")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)


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
) -> FrameioWebhookService:
    """
    Provide the webhook service dependency.

    This is where we wire the core service with its infrastructure dependencies.
    """
    return FrameioWebhookService(event_publisher=event_publisher)


# Override the dependency in the router to use our wired service
app.dependency_overrides[get_webhook_service_dependency] = get_webhook_service


# ============================================================================
# Centralized Exception Handlers
# ============================================================================


@app.exception_handler(PublisherError)
async def publisher_error_handler(request: Request, exc: PublisherError):
    """
    Handle publisher errors (Pub/Sub failures).

    Returns 500 Internal Server Error so Frame.io will retry the webhook.
    This prevents data loss when Pub/Sub is temporarily unavailable.
    """
    logger.error(f"Publisher error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Failed to publish event - please retry",
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors (invalid JSON or missing fields).

    Returns 422 Unprocessable Entity so Frame.io knows not to retry.
    Logs the raw request body for debugging.
    """
    # Log the validation error with raw body for debugging
    body = await request.body()
    logger.error(
        f"Validation error: {str(exc)}\n"
        f"Raw body: {body.decode('utf-8') if body else 'empty'}"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Invalid payload schema",
            "details": exc.errors(),
        },
    )


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
# Protected Endpoints
# ============================================================================


@app.get("/dashboard")
async def dashboard(current_user: dict = Depends(get_current_user)):
    """
    Protected dashboard endpoint.

    Requires a valid session cookie to access.

    Args:
        current_user: User claims from validated session cookie

    Returns:
        Welcome message with user information
    """
    user_email = current_user.get("email", "unknown")
    user_uid = current_user.get("uid", "unknown")

    logger.info(f"Dashboard accessed by user: {user_uid}")

    return {
        "status": "success",
        "message": "Welcome, you are authenticated!",
        "user": {
            "uid": user_uid,
            "email": user_email,
        },
    }


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(frameio.router)
app.include_router(magic.router)
app.include_router(oauth_router.router)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
