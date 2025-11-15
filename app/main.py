"""
FastAPI application for receiving Frame.io webhooks.
Logs webhook payloads to stdout for viewing in GCP Cloud Run logs.
"""

import json
import logging
import os
from datetime import datetime, UTC

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Frame.io Webhook Receiver",
    description="Receives and logs Frame.io V4 webhooks",
    version="1.0.0",
)


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
async def frameio_webhook(request: Request):
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

        # Log the webhook data with structured information
        logger.info("=" * 80)
        logger.info("FRAME.IO WEBHOOK RECEIVED")
        logger.info("=" * 80)
        logger.info(f"Event Type: {event_type}")
        logger.info(f"Resource Type: {resource_type}")
        logger.info(f"Resource ID: {resource_id}")
        logger.info(f"Account ID: {account_id}")
        logger.info(f"Workspace ID: {workspace_id}")
        logger.info(f"Project ID: {project_id}")
        logger.info(f"User ID: {user_id}")
        logger.info(f"User Agent: {user_agent}")
        logger.info(f"Timestamp: {datetime.now(UTC).isoformat()}")
        logger.info(
            f"Client IP: {request.client.host if request.client else 'unknown'}"
        )
        logger.info("-" * 80)
        logger.info("HEADERS:")
        logger.info(json.dumps(headers, indent=2, default=str))
        logger.info("-" * 80)
        logger.info("FULL PAYLOAD:")
        logger.info(json.dumps(payload, indent=2, default=str))
        logger.info("=" * 80)

        # Return success response
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "received",
                "event_type": event_type,
                "resource_type": resource_type,
                "timestamp": datetime.now(UTC).isoformat(),
            },
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
