"""
Tests for the OAuth 2.0 authorization flow.
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from starlette.responses import RedirectResponse

from app.main import app

client = TestClient(app)


@patch(
    "app.infrastructure.oauth_providers.AdobeOAuthProvider.authorize_redirect",
    new_callable=AsyncMock,
)
def test_login_adobe_redirects(mock_authorize_redirect):
    """Test that the /login/adobe endpoint redirects the user."""
    # Configure the mock to return a RedirectResponse
    redirect_url = "https://ims-na1.adobelogin.com/ims/authorize?..."
    mock_authorize_redirect.return_value = RedirectResponse(url=redirect_url)

    # Make the request to the endpoint, but don't follow the redirect
    response = client.get("/login/adobe", follow_redirects=False)

    # Assert that the response is a redirect
    assert response.status_code == 307
    assert response.headers["location"] == redirect_url
    mock_authorize_redirect.assert_called_once()


@patch(
    "app.infrastructure.oauth_providers.AdobeOAuthProvider.authorize_access_token",
    new_callable=AsyncMock,
)
def test_auth_adobe_callback(mock_authorize_access_token, caplog):
    """Test that the /auth/adobe endpoint handles the callback correctly."""
    # Configure the mock to return a dummy token
    dummy_token = {
        "access_token": "dummy_access_token",
        "refresh_token": "dummy_refresh_token",
    }
    mock_authorize_access_token.return_value = dummy_token

    # Make the request to the endpoint
    response = client.get("/auth/adobe")

    # Assert that the response is successful
    assert response.status_code == 200
    assert response.json() == {"message": "Successfully authorized with Adobe."}

    # Assert that the token was logged
    assert "Adobe Access Token: dummy_access_token" in caplog.text
    assert "Adobe Refresh Token: dummy_refresh_token" in caplog.text
    mock_authorize_access_token.assert_called_once()
