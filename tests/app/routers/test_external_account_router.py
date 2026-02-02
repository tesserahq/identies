"""Tests for external account router."""

from uuid import uuid4

import pytest


def test_create_link_token_unauthenticated(client, faker):
    """POST /external-accounts/link-tokens works without auth."""
    payload = {
        "platform": "telegram",
        "external_user_id": faker.numerify(text="##########"),
    }
    response = client.post("/external-accounts/link-tokens", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "expires_at" in data
    assert data["token"]
    assert data["expires_at"]


def test_create_link_token_with_data_and_ttl(client, faker):
    """POST /external-accounts/link-tokens with optional data and expires_in_seconds."""
    payload = {
        "platform": "telegram",
        "external_user_id": faker.numerify(text="##########"),
        "data": {"username": "testbot"},
        "expires_in_seconds": 300,
    }
    response = client.post("/external-accounts/link-tokens", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["token"]
    assert data["expires_at"]


def test_link_external_account_success(client, setup_user, setup_link_token):
    """POST /external-accounts/link with valid token returns ExternalAccountResponse."""
    link_token = setup_link_token
    response = client.post(
        "/external-accounts/link",
        json={"token": link_token.token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(setup_user.id)
    assert data["platform"] == link_token.platform
    assert data["external_id"] == link_token.external_id
    assert "id" in data
    assert "data" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_link_external_account_invalid_token(client):
    """POST /external-accounts/link with invalid token returns 400."""
    response = client.post(
        "/external-accounts/link",
        json={"token": "invalid-token-value"},
    )
    assert response.status_code == 400
    assert "detail" in response.json()


def test_link_external_account_expired_token(client, setup_expired_link_token):
    """POST /external-accounts/link with expired token returns 400."""
    response = client.post(
        "/external-accounts/link",
        json={"token": setup_expired_link_token.token},
    )
    assert response.status_code == 400


def test_link_external_account_used_token(client, setup_user, setup_link_token):
    """POST /external-accounts/link with already-used token returns 400."""
    link_token = setup_link_token
    first = client.post(
        "/external-accounts/link",
        json={"token": link_token.token},
    )
    assert first.status_code == 200
    second = client.post(
        "/external-accounts/link",
        json={"token": link_token.token},
    )
    assert second.status_code == 400


def test_list_external_accounts_paginated(client, setup_user, setup_external_account):
    """GET /external-accounts returns paginated list for current user."""
    response = client.get("/external-accounts")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data
    assert data["total"] >= 1
    account = setup_external_account
    ids = [item["id"] for item in data["items"]]
    assert str(account.id) in ids


def test_list_external_accounts_empty(client, setup_user):
    """GET /external-accounts returns empty list when user has none."""
    response = client.get("/external-accounts")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_delete_external_account_success(client, setup_user, setup_external_account):
    """DELETE /external-accounts/{id} returns 204 when owner."""
    account = setup_external_account
    response = client.delete(f"/external-accounts/{account.id}")
    assert response.status_code == 204
    list_resp = client.get("/external-accounts")
    ids = [item["id"] for item in list_resp.json()["items"]]
    assert str(account.id) not in ids


def test_delete_external_account_not_found(client, setup_user):
    """DELETE /external-accounts/{id} returns 404 for non-existent id."""
    response = client.delete(f"/external-accounts/{uuid4()}")
    assert response.status_code == 404


def test_delete_external_account_other_user_returns_404(
    client, setup_user, setup_another_user, setup_external_account
):
    """DELETE /external-accounts/{id} for another user's account returns 404 (not 403)."""
    account = setup_external_account
    assert account.user_id == setup_user.id
    client_other = client
    client.app.state.test_user = setup_another_user
    response = client_other.delete(f"/external-accounts/{account.id}")
    client.app.state.test_user = setup_user
    assert response.status_code == 404
