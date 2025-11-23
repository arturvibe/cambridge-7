"""
Unit tests for the Frame.io source client.
"""

import httpx
import pytest
from respx import MockRouter

from app.core.domain import FrameioFile
from app.core.exceptions import FrameioClientError
from app.infrastructure.frameio_client import FrameioSourceClient


@pytest.mark.asyncio
async def test_get_file_url_success(respx_mock: MockRouter):
    """
    Test get_file_url successfully retrieves and parses the file URL.
    """
    mock_response = {
        "name": "test_file.mov",
        "media_links": {"original": {"download_url": "https://example.com/download"}},
    }
    respx_mock.get("https://api.frame.io/v4/accounts/123/files/456").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    client = FrameioSourceClient()
    result = await client.get_file_url(
        token="test_token", account_id="123", file_id="456"
    )

    assert isinstance(result, FrameioFile)
    assert result.name == "test_file.mov"
    assert result.url == "https://example.com/download"


@pytest.mark.asyncio
async def test_get_file_url_http_error(respx_mock: MockRouter):
    """
    Test get_file_url raises FrameioClientError on HTTP status error.
    """
    respx_mock.get("https://api.frame.io/v4/accounts/123/files/456").mock(
        return_value=httpx.Response(500)
    )

    client = FrameioSourceClient()
    with pytest.raises(FrameioClientError, match="API request failed"):
        await client.get_file_url(
            token="test_token", account_id="123", file_id="456"
        )


@pytest.mark.asyncio
async def test_get_file_url_validation_error(respx_mock: MockRouter):
    """
    Test get_file_url raises FrameioClientError on Pydantic validation error.
    """
    mock_response = {"invalid": "data"}
    respx_mock.get("https://api.frame.io/v4/accounts/123/files/456").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    client = FrameioSourceClient()
    with pytest.raises(FrameioClientError, match="Invalid API response"):
        await client.get_file_url(
            token="test_token", account_id="123", file_id="456"
        )


@pytest.mark.asyncio
async def test_get_file_url_network_error(respx_mock: MockRouter):
    """
    Test get_file_url raises FrameioClientError on network error.
    """
    respx_mock.get("https://api.frame.io/v4/accounts/123/files/456").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    client = FrameioSourceClient()
    with pytest.raises(FrameioClientError):
        await client.get_file_url(
            token="test_token", account_id="123", file_id="456"
        )
