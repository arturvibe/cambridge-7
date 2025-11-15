"""
FastAPI application for receiving Frame.io webhooks.
Logs webhook payloads to stdout for viewing in GCP Cloud Run logs.
"""

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response, status, HTTPException
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
FRAMEIO_WEBHOOK_SECRET = os.getenv("FRAMEIO_WEBHOOK_SECRET")
VERIFY_SIGNATURES = os.getenv("VERIFY_SIGNATURES", "true").lower() == "true"
SIGNATURE_TIME_TOLERANCE = int(os.getenv("SIGNATURE_TIME_TOLERANCE", "300"))  # 5 minutes

app = FastAPI(
    title="Frame.io Webhook Receiver",
    description="Receives and logs Frame.io webhooks with signature verification",
    version="1.0.0"
)


def verify_frameio_signature(
    timestamp: str,
    signature: str,
    body: bytes,
    secret: str
) -> bool:
    """
    Verify Frame.io webhook signature.

    Args:
        timestamp: Request timestamp from X-Frameio-Request-Timestamp header
        signature: Signature from X-Frameio-Signature header
        body: Raw request body
        secret: Webhook signing secret

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Check timestamp to prevent replay attacks
        current_time = int(time.time())
        request_time = int(timestamp)

        if abs(current_time - request_time) > SIGNATURE_TIME_TOLERANCE:
            logger.warning(
                f"Webhook timestamp outside tolerance window: "
                f"current={current_time}, request={request_time}, "
                f"diff={abs(current_time - request_time)}s"
            )
            return False

        # Create signature string: v0:timestamp:body
        message = f"v0:{timestamp}:{body.decode('utf-8')}"

        # Calculate HMAC SHA256
        calculated_signature = hmac.new(
            bytes(secret, 'latin-1'),
            msg=bytes(message, 'latin-1'),
            digestmod=hashlib.sha256
        ).hexdigest()

        # Add v0= prefix to match Frame.io format
        calculated_signature = f"v0={calculated_signature}"

        # Compare signatures
        is_valid = hmac.compare_digest(calculated_signature, signature)

        if not is_valid:
            logger.warning(
                f"Signature mismatch: expected={calculated_signature}, "
                f"received={signature}"
            )

        return is_valid

    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}", exc_info=True)
        return False


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
    This endpoint receives the payload, optionally verifies the signature,
    and logs it for inspection.

    Security headers expected from Frame.io:
    - X-Frameio-Request-Timestamp: Unix timestamp when request was sent
    - X-Frameio-Signature: HMAC SHA256 signature (v0=<hash>)
    - User-Agent: Frame.io V4 API
    """
    try:
        # Get the raw body
        body = await request.body()

        # Get headers
        headers = dict(request.headers)

        # Extract Frame.io specific headers
        frameio_timestamp = headers.get("x-frameio-request-timestamp")
        frameio_signature = headers.get("x-frameio-signature")
        user_agent = headers.get("user-agent", "")

        # Verify signature if enabled and secret is configured
        if VERIFY_SIGNATURES:
            if not FRAMEIO_WEBHOOK_SECRET:
                logger.error(
                    "Signature verification enabled but FRAMEIO_WEBHOOK_SECRET not set"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Webhook signature verification not properly configured"
                )

            if not frameio_timestamp or not frameio_signature:
                logger.warning(
                    "Missing Frame.io signature headers: "
                    f"timestamp={frameio_timestamp}, signature={frameio_signature}"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing required signature headers"
                )

            if not verify_frameio_signature(
                frameio_timestamp,
                frameio_signature,
                body,
                FRAMEIO_WEBHOOK_SECRET
            ):
                logger.error("Invalid webhook signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature"
                )

        # Parse JSON payload
        try:
            payload = json.loads(body.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to parse JSON payload: {str(e)}")
            payload = {"raw_body": body.decode('utf-8') if body else None}

        # Extract Frame.io webhook structure
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
        logger.info(f"Signature Verified: {VERIFY_SIGNATURES}")
        logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
        logger.info(f"Client IP: {request.client.host if request.client else 'unknown'}")
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
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

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
