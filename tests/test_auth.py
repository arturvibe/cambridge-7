from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_firebase_auth():
    with patch("app.core.services.auth") as mock_auth:
        yield mock_auth

@patch("app.core.services.timedelta")
def test_session_login(mock_timedelta, mock_firebase_auth):
    mock_firebase_auth.create_session_cookie.return_value = "test_session_cookie"
    response = client.post("/auth/session-login", json={"id_token": "test_id_token"})
    assert response.status_code == 200
    assert response.json() == {"message": "Session created successfully."}
    mock_firebase_auth.create_session_cookie.assert_called_once()
    assert "session" in response.cookies

def test_get_user_profile_unauthenticated():
    response = client.get("/users/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

@patch("app.core.services.auth.verify_session_cookie")
def test_get_user_profile_authenticated(mock_verify_session_cookie):
    mock_verify_session_cookie.return_value = {"uid": "test_uid"}
    response = client.get("/users/me", cookies={"session": "test_session_cookie"})
    assert response.status_code == 200
    assert response.json() == {"uid": "test_uid"}
    mock_verify_session_cookie.assert_called_once_with("test_session_cookie", check_revoked=True)
