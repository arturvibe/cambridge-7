"""
Frame.io webhook API endpoints.

This is a driving adapter that exposes HTTP endpoints for receiving
Frame.io webhooks and delegates to the core domain service.
"""

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.core.domain import FrameIOEvent
from app.core.services import FrameioWebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/frameio", tags=["frameio"])


def get_webhook_service_dependency() -> FrameioWebhookService:
    """
    Placeholder dependency function for FrameioWebhookService.

    This will be overridden in main.py via app.dependency_overrides.
    """
    raise NotImplementedError("FrameioWebhookService dependency must be configured")


@router.post("/webhook")
async def frameio_webhook(
    request: Request,
    webhook_service: FrameioWebhookService = Depends(get_webhook_service_dependency),
):
    """
    Receive Frame.io webhook and process event.

    Frame.io sends webhooks when events occur (e.g., new file created).
    This endpoint receives the payload, logs it, and publishes to Pub/Sub.

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

        # Extract Frame.io V4 webhook structure for logging
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

        # Parse payload into domain model
        event = FrameIOEvent(**payload)

        # Process webhook through core service
        result = webhook_service.process_webhook(event)

        # Add timestamp to response
        result["timestamp"] = datetime.now(UTC).isoformat()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result,
        )

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": str(e)},
        )
