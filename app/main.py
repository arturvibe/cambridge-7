"""
FastAPI application for receiving Frame.io webhooks.
Logs webhook payloads to stdout for viewing in GCP Cloud Run logs.
"""

import json
import logging
import os
from datetime import datetime, UTC
from functools import lru_cache

# Configure logging FIRST, before other local imports
from app.logging_config import setup_global_logging

setup_global_logging()

# Now import other modules (they will use the configured logging)
from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.pubsub_client import PubSubClient

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Frame.io Webhook Receiver",
    description="Receives and logs Frame.io V4 webhooks",
    version="1.0.0",
)


@lru_cache()
def get_pubsub_client() -> PubSubClient:
    """
    Dependency that provides the Pub/Sub client.

    Uses lru_cache to ensure singleton behavior - the same instance
    is returned for all requests.
    """
    return PubSubClient()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down application...")
    try:
        # Close the Pub/Sub client (handles both real and mocked clients)
        get_pubsub_client().close()
    except Exception as e:
        # Gracefully handle shutdown errors (e.g., client not initialized)
        logger.warning(f"Error closing Pub/Sub client during shutdown: {e}")


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


@app.post("/api/v1/frameio/webhook")
async def frameio_webhook(
    request: Request, pubsub_client: PubSubClient = Depends(get_pubsub_client)
):
    """
    Receive Frame.io webhook and log payload to stdout.

    Frame.io sends webhooks when events occur (e.g., new file created).
    This endpoint receives the payload and logs it for inspection.

    Expected from Frame.io V4:
    - User-Agent: Frame.io V4 API
    - Payload structure with type, resource, account, workspace, project, user
    """
    try:
        # Get the raw body
        body = await request.body()

        # Get headers
        headers = dict(request.headers)
        user_agent = headers.get("user-agent", "")

        # Parse JSON payload
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to parse JSON payload: {str(e)}")
            payload = {"raw_body": body.decode("utf-8") if body else None}

        # Extract Frame.io V4 webhook structure
        event_type = payload.get("type", "unknown")
        resource = payload.get("resource", {})
        resource_type = resource.get("type", "unknown")
        resource_id = resource.get("id", "unknown")
        account_id = payload.get("account", {}).get("id")
        workspace_id = payload.get("workspace", {}).get("id")
        project_id = payload.get("project", {}).get("id")
        user_id = payload.get("user", {}).get("id")

        # Log webhook data as structured JSON for Cloud Logging
        # Single log entry with jsonPayload and automatic trace correlation
        log_data = {
            "message": "FRAME.IO WEBHOOK RECEIVED",
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "account_id": account_id,
            "workspace_id": workspace_id,
            "project_id": project_id,
            "user_id": user_id,
            "user_agent": user_agent,
            "timestamp": datetime.now(UTC).isoformat(),
            "client_ip": request.client.host if request.client else "unknown",
            "headers": headers,
            "payload": payload,
        }

        # Log as structured JSON - Cloud Logging will populate jsonPayload field
        logger.info(json.dumps(log_data, default=str))

        # Publish to Pub/Sub
        pubsub_message_id = None
        try:
            pubsub_message_id = pubsub_client.publish(
                message_data=payload,
                attributes={
                    "event_type": event_type,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                },
            )
            if pubsub_message_id:
                logger.info(
                    f"Published to Pub/Sub with message ID: {pubsub_message_id}"
                )
        except Exception as e:
            # Don't fail the webhook if Pub/Sub publishing fails
            logger.error(f"Failed to publish to Pub/Sub: {str(e)}", exc_info=True)

        # Return success response
        response_content = {
            "status": "received",
            "event_type": event_type,
            "resource_type": resource_type,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Include Pub/Sub message ID in response if available
        if pubsub_message_id:
            response_content["pubsub_message_id"] = pubsub_message_id

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_content,
        )

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": str(e)},
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
