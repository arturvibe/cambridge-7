"""
Frame.io webhook API endpoints.

This is a driving adapter that exposes HTTP endpoints for receiving
Frame.io webhooks and delegates to the core domain service.

The adapter is "dumb" - it only translates HTTP to Python and back.
All business logic lives in the service layer.
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.core.domain import FrameIOEvent
from app.core.services import FrameioWebhookService

router = APIRouter(prefix="/api/v1/frameio", tags=["frameio"])


def get_webhook_service_dependency() -> FrameioWebhookService:
    """
    Placeholder dependency function for FrameioWebhookService.

    This will be overridden in main.py via app.dependency_overrides.
    """
    raise NotImplementedError("FrameioWebhookService dependency must be configured")


@router.post("/webhook")
async def frameio_webhook(
    event: FrameIOEvent,
    request: Request,
    webhook_service: FrameioWebhookService = Depends(get_webhook_service_dependency),
):
    """
    Receive Frame.io webhook and process event.

    This endpoint is a "dumb adapter" - it only translates HTTP to Python.
    All business logic (logging, publishing, error handling) is in the service.

    FastAPI automatically:
    - Parses JSON body (returns 422 if invalid JSON)
    - Validates against FrameIOEvent model (returns 422 if validation fails)

    Exception handling is centralized in main.py:
    - PublisherError -> 500 (Frame.io retries)
    - RequestValidationError -> 422 (Frame.io does not retry)

    Expected from Frame.io V4:
    - User-Agent: Frame.io V4 API
    - Payload structure with type, resource, account, workspace, project, user
    """
    # Delegate to core service - all business logic happens there
    message_id = webhook_service.process_webhook(
        event=event,
        headers=dict(request.headers),
        client_ip=request.client.host if request.client else "unknown",
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message_id": message_id},
    )
