"""
FastAPI application for receiving Frame.io webhooks.
Logs webhook payloads to stdout for viewing in GCP Cloud Run logs.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Frame.io Webhook Receiver",
    description="Receives and logs Frame.io webhooks",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "frameio-webhook-receiver",
        "timestamp": datetime.utcnow().isoformat()
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
    """
    try:
        # Get the raw body
        body = await request.body()

        # Get headers
        headers = dict(request.headers)

        # Parse JSON payload
        try:
            payload = await request.json()
        except Exception:
            payload = body.decode('utf-8') if body else None

        # Log the webhook data
        logger.info("=" * 80)
        logger.info("FRAME.IO WEBHOOK RECEIVED")
        logger.info("=" * 80)
        logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
        logger.info(f"Client IP: {request.client.host if request.client else 'unknown'}")
        logger.info("-" * 80)
        logger.info("HEADERS:")
        logger.info(json.dumps(headers, indent=2, default=str))
        logger.info("-" * 80)
        logger.info("PAYLOAD:")
        logger.info(json.dumps(payload, indent=2, default=str))
        logger.info("=" * 80)

        # Return success response
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "received", "timestamp": datetime.utcnow().isoformat()}
        )

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": str(e)}
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
