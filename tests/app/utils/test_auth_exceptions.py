"""Tests for custom auth exceptions."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.utils.auth import InviteOnlyAccessException


def test_invite_only_access_exception():
    """Test InviteOnlyAccessException returns correct payload."""
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
