"""Tests for custom auth exceptions."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.auth.exceptions import InviteOnlyAccessException


def test_invite_only_access_exception():
    """Test InviteOnlyAccessException returns correct payload without email."""
    app = FastAPI()

    @app.get("/test")
    def test_endpoint():
        raise InviteOnlyAccessException()

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 403
    response_data = response.json()

    assert "detail" in response_data
    detail = response_data["detail"]

    assert detail["title"] == "Access not granted"
    assert detail["detail"] == "Invitation required to access this service."
    assert detail["code"] == "INVITE_REQUIRED"
    assert "email" not in detail


def test_invite_only_access_exception_with_email():
    """Test InviteOnlyAccessException returns correct payload with email."""
    app = FastAPI()

    @app.get("/test")
    def test_endpoint():
        raise InviteOnlyAccessException(email="test@example.com")

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 403
    response_data = response.json()

    assert "detail" in response_data
    detail = response_data["detail"]

    assert detail["title"] == "Access not granted"
    assert detail["detail"] == "Invitation required to access this service."
    assert detail["code"] == "INVITE_REQUIRED"
    assert detail["email"] == "test@example.com"


def test_invite_only_access_exception_with_custom_message_and_email():
    """Test InviteOnlyAccessException with custom message and email."""
    app = FastAPI()

    @app.get("/test")
    def test_endpoint():
        raise InviteOnlyAccessException(
            detail="Custom access denied message", email="user@company.com"
        )

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 403
    response_data = response.json()

    assert "detail" in response_data
    detail = response_data["detail"]

    assert detail["title"] == "Access not granted"
    assert detail["detail"] == "Custom access denied message"
    assert detail["code"] == "INVITE_REQUIRED"
    assert detail["email"] == "user@company.com"
