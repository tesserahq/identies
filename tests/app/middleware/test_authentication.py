"""Tests for authentication middleware."""

import pytest
from unittest.mock import Mock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.middleware.authentication import AuthenticationMiddleware
from app.utils.auth import InviteOnlyAccessException


@pytest.fixture
def app():
    """Create a FastAPI app with authentication middleware for testing."""
    app = FastAPI()
    app.add_middleware(AuthenticationMiddleware)

    @app.get("/protected")
    def protected_endpoint():
        return {"message": "Access granted"}

    @app.get("/health")
    def health_endpoint():
        return {"status": "healthy"}

    return app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return TestClient(app)


def test_health_endpoint_bypasses_auth(client):
    """Test that health endpoint bypasses authentication."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_protected_endpoint_without_token(client):
    """Test that protected endpoint returns 401 without token."""
    response = client.get("/protected")
    assert response.status_code == 401
    assert response.json() == {"error": "Missing or invalid token"}


def test_protected_endpoint_with_invalid_token_format(client):
    """Test that protected endpoint returns 401 with invalid token format."""
    response = client.get(
        "/protected", headers={"Authorization": "InvalidFormat token123"}
    )
    assert response.status_code == 401
    assert response.json() == {"error": "Missing or invalid token"}


def test_protected_endpoint_with_invite_only_exception(client):
    """Test that InviteOnlyAccessException is properly handled."""
    with patch("app.middleware.authentication.verify_token_dependency") as mock_verify:
        # Mock the verify_token_dependency to raise InviteOnlyAccessException
        mock_verify.side_effect = InviteOnlyAccessException("Custom invite message")

        response = client.get(
            "/protected", headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 403
        response_data = response.json()

        # Check that the custom exception detail is returned
        assert "title" in response_data
        assert "detail" in response_data
        assert "code" in response_data
        assert response_data["title"] == "Access not granted"
        assert response_data["detail"] == "Custom invite message"
        assert response_data["code"] == "INVITE_REQUIRED"


def test_protected_endpoint_with_invite_only_exception_with_email(client):
    """Test that InviteOnlyAccessException with email is properly handled."""
    with patch("app.middleware.authentication.verify_token_dependency") as mock_verify:
        # Mock the verify_token_dependency to raise InviteOnlyAccessException with email
        mock_verify.side_effect = InviteOnlyAccessException(
            "Custom invite message", email="test@example.com"
        )

        response = client.get(
            "/protected", headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 403
        response_data = response.json()

        # Check that the custom exception detail is returned with email
        assert "title" in response_data
        assert "detail" in response_data
        assert "code" in response_data
        assert "email" in response_data
        assert response_data["title"] == "Access not granted"
        assert response_data["detail"] == "Custom invite message"
        assert response_data["code"] == "INVITE_REQUIRED"
        assert response_data["email"] == "test@example.com"


def test_protected_endpoint_with_default_invite_only_exception(client):
    """Test that InviteOnlyAccessException with default message is properly handled."""
    with patch("app.middleware.authentication.verify_token_dependency") as mock_verify:
        # Mock the verify_token_dependency to raise InviteOnlyAccessException with default message
        mock_verify.side_effect = InviteOnlyAccessException()

        response = client.get(
            "/protected", headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 403
        response_data = response.json()

        # Check that the default exception detail is returned
        assert response_data["title"] == "Access not granted"
        assert response_data["detail"] == "Invitation required to access this service."
        assert response_data["code"] == "INVITE_REQUIRED"
        assert "email" not in response_data


def test_protected_endpoint_with_default_invite_only_exception_with_email(client):
    """Test that InviteOnlyAccessException with default message and email is properly handled."""
    with patch("app.middleware.authentication.verify_token_dependency") as mock_verify:
        # Mock the verify_token_dependency to raise InviteOnlyAccessException with default message and email
        mock_verify.side_effect = InviteOnlyAccessException(email="user@company.com")

        response = client.get(
            "/protected", headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 403
        response_data = response.json()

        # Check that the default exception detail is returned with email
        assert response_data["title"] == "Access not granted"
        assert response_data["detail"] == "Invitation required to access this service."
        assert response_data["code"] == "INVITE_REQUIRED"
        assert response_data["email"] == "user@company.com"


def test_protected_endpoint_with_unauthorized_exception(client):
    """Test that HTTPException with 401 status is properly handled."""
    from fastapi import HTTPException, status

    with patch("app.middleware.authentication.verify_token_dependency") as mock_verify:
        # Mock the verify_token_dependency to raise HTTPException with 401
        mock_verify.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

        response = client.get(
            "/protected", headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401
        assert response.json() == {"error": "Invalid token"}


def test_protected_endpoint_with_forbidden_exception(client):
    """Test that HTTPException with 403 status is properly handled."""
    from fastapi import HTTPException, status

    with patch("app.middleware.authentication.verify_token_dependency") as mock_verify:
        # Mock the verify_token_dependency to raise HTTPException with 403
        mock_verify.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
        )

        response = client.get(
            "/protected", headers={"Authorization": "Bearer forbidden_token"}
        )

        assert response.status_code == 403
        assert response.json() == {"error": "Forbidden"}


def test_protected_endpoint_with_successful_auth(client):
    """Test that successful authentication allows access."""
    with patch("app.middleware.authentication.verify_token_dependency") as mock_verify:
        # Mock the verify_token_dependency to not raise any exception
        mock_verify.return_value = None

        response = client.get(
            "/protected", headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        assert response.json() == {"message": "Access granted"}


def test_x_api_key_bypasses_bearer_auth(client):
    """Test that X-API-Key header bypasses Bearer token authentication."""
    with patch("app.middleware.authentication.verify_token_dependency") as mock_verify:
        # Mock should not be called when X-API-Key is present
        mock_verify.return_value = None

        response = client.get("/protected", headers={"X-API-Key": "test_api_key"})

        # The middleware should pass through to the endpoint
        # Since we're not actually implementing API key auth in the endpoint,
        # it will likely return 200 if the endpoint doesn't require auth
        assert response.status_code == 200
        assert response.json() == {"message": "Access granted"}
