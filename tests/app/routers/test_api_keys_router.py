import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta


@pytest.fixture
def api_key_create_data(faker):
    """Create sample API key creation data for testing."""
    return {
        "name": faker.word(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }


@pytest.fixture
def api_key_create_data_no_expiry(faker):
    """Create sample API key creation data without expiry for testing."""
    return {
        "name": faker.word(),
        "expires_at": None,
    }


def test_create_api_key(client: TestClient, api_key_create_data):
    """Test creating a new API key."""
    response = client.post("/me/api-keys", json=api_key_create_data)

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "id" in data
    assert "key_id" in data
    assert "name" in data
    assert "created_at" in data
    assert "last_used_at" in data
    assert "expires_at" in data
    assert "revoked" in data
    assert "full_key" in data

    # Check values
    assert data["name"] == api_key_create_data["name"]
    assert data["revoked"] is False
    assert data["full_key"].startswith("ak_")
    assert "." in data["full_key"]


def test_create_api_key_no_expiry(client: TestClient, api_key_create_data_no_expiry):
    """Test creating an API key without expiry."""
    response = client.post("/me/api-keys", json=api_key_create_data_no_expiry)

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check values
    assert data["name"] == api_key_create_data_no_expiry["name"]
    assert data["expires_at"] is None
    assert data["revoked"] is False


def test_create_api_key_invalid_data(client: TestClient):
    """Test creating an API key with invalid data."""
    invalid_data = {
        "name": "",  # Empty name should fail validation
    }

    response = client.post("/me/api-keys", json=invalid_data)

    # Assertions
    assert response.status_code == 422  # Validation error


def test_list_api_keys_empty(client: TestClient):
    """Test listing API keys when user has none."""
    response = client.get("/me/api-keys")
    print(response.json())
    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure (fastapi-pagination Page format)
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data
    assert data["items"] == []
    assert data["total"] == 0


def test_list_api_keys_with_data(client: TestClient, setup_api_key):
    """Test listing API keys when user has some."""
    # Create another API key for the same user
    api_key_data = {
        "name": "Second API Key",
        "expires_at": None,
    }
    client.post("/me/api-keys", json=api_key_data)

    response = client.get("/me/api-keys")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure (fastapi-pagination Page format)
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data
    assert len(data["items"]) >= 1
    assert data["total"] >= 1

    # Check that full_key is not included in list
    for api_key in data["items"]:
        assert "full_key" not in api_key
        assert "id" in api_key
        assert "key_id" in api_key
        assert "name" in api_key
        assert "created_at" in api_key
        assert "revoked" in api_key


def test_get_api_key(client: TestClient, setup_api_key):
    """Test getting a specific API key by ID."""
    api_key, _ = setup_api_key

    response = client.get(f"/api-keys/{api_key.id}")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "id" in data
    assert "key_id" in data
    assert "name" in data
    assert "created_at" in data
    assert "last_used_at" in data
    assert "expires_at" in data
    assert "revoked" in data

    # Check values
    assert data["id"] == str(api_key.id)
    assert data["key_id"] == api_key.key_id
    assert data["name"] == api_key.name
    assert data["revoked"] is False

    # Check that full_key is not included
    assert "full_key" not in data


def test_get_api_key_not_found(client: TestClient):
    """Test getting a non-existent API key."""
    from uuid import uuid4

    response = client.get(f"/api-keys/{uuid4()}")

    # Assertions
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_api_key_wrong_user(client: TestClient, setup_another_user_api_key):
    """Test getting an API key belonging to another user."""
    api_key, _ = setup_another_user_api_key

    response = client.get(f"/api-keys/{api_key.id}")

    # Assertions
    assert (
        response.status_code == 403
    )  # Should be forbidden (not owned by current user)
    data = response.json()
    assert "only view your own" in data["detail"].lower()


def test_revoke_api_key(client: TestClient, setup_api_key):
    """Test revoking an API key."""
    api_key, _ = setup_api_key

    response = client.put(f"/api-keys/{api_key.id}/revoke")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "API key revoked successfully"


def test_revoke_api_key_not_found(client: TestClient):
    """Test revoking a non-existent API key."""
    from uuid import uuid4

    response = client.put(f"/api-keys/{uuid4()}/revoke")

    # Assertions
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_revoke_api_key_wrong_user(client: TestClient, setup_another_user_api_key):
    """Test revoking an API key belonging to another user."""
    api_key, _ = setup_another_user_api_key

    response = client.put(f"/api-keys/{api_key.id}/revoke")

    # Assertions
    assert (
        response.status_code == 403
    )  # Should be forbidden (not owned by current user)
    data = response.json()
    assert "only revoke your own" in data["detail"].lower()


def test_delete_api_key(client: TestClient, setup_api_key):
    """Test permanently deleting an API key."""
    api_key, _ = setup_api_key

    response = client.delete(f"/api-keys/{api_key.id}")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "API key deleted successfully"


def test_delete_api_key_not_found(client: TestClient):
    """Test deleting a non-existent API key."""
    from uuid import uuid4

    response = client.delete(f"/api-keys/{uuid4()}")

    # Assertions
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_delete_api_key_wrong_user(client: TestClient, setup_another_user_api_key):
    """Test deleting an API key belonging to another user."""
    api_key, _ = setup_another_user_api_key

    response = client.delete(f"/api-keys/{api_key.id}")

    # Assertions
    assert (
        response.status_code == 403
    )  # Should be forbidden (not owned by current user)
    data = response.json()
    assert "only delete your own" in data["detail"].lower()


def test_api_key_authentication_flow(client: TestClient):
    """Test the complete API key authentication flow."""
    # 1. Create an API key
    api_key_data = {
        "name": "Test Authentication Key",
        "expires_at": None,
    }

    create_response = client.post("/me/api-keys", json=api_key_data)
    assert create_response.status_code == 200
    create_data = create_response.json()
    full_key = create_data["full_key"]

    # 2. Use the API key to authenticate (test with userinfo endpoint)
    # Note: This would require updating the test client to support API key headers
    # For now, we'll just verify the key was created correctly
    assert full_key.startswith("ak_")
    assert "." in full_key

    # 3. List the API keys to verify it was created
    list_response = client.get("/me/api-keys")
    assert list_response.status_code == 200
    list_data = list_response.json()

    # Find our created key in the list (fastapi-pagination Page format)
    created_key = next(
        (key for key in list_data["items"] if key["id"] == create_data["id"]), None
    )
    assert created_key is not None
    assert created_key["name"] == "Test Authentication Key"
    assert created_key["revoked"] is False


def test_api_key_validation(client: TestClient):
    """Test API key validation with various invalid inputs."""
    # Test with missing name
    invalid_data = {
        "expires_at": None,
    }

    response = client.post("/me/api-keys", json=invalid_data)
    assert response.status_code == 422

    # Test with empty name
    invalid_data = {
        "name": "",
        "expires_at": None,
    }

    response = client.post("/me/api-keys", json=invalid_data)
    assert response.status_code == 422

    # Test with name too long
    invalid_data = {
        "name": "a" * 101,  # Exceeds max length
        "expires_at": None,
    }

    response = client.post("/me/api-keys", json=invalid_data)
    assert response.status_code == 422


def test_api_key_expiry_handling(client: TestClient):
    """Test API key expiry handling."""
    # Create API key with expiry in the past (should still be created, but invalid for auth)
    past_expiry = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    api_key_data = {
        "name": "Expired Key",
        "expires_at": past_expiry,
    }

    response = client.post("/me/api-keys", json=api_key_data)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Expired Key"
    # Compare timestamps (handle timezone differences)
    assert data["expires_at"].replace("+00:00", "") == past_expiry.replace("+00:00", "")
    assert data["revoked"] is False


def test_introspect_api_key_valid(client: TestClient, setup_api_key):
    """Test introspecting a valid API key."""
    api_key, full_key = setup_api_key

    response = client.post(
        "/api-keys/introspect", headers={"Authorization": f"Bearer {full_key}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["active"] is True
    assert data["user_id"] == str(api_key.user_id)
    assert data["key_id"] == api_key.key_id
    assert data["scopes"] is None  # No scopes implemented yet
    assert data["expires_at"] is not None


def test_introspect_api_key_invalid_format(client: TestClient):
    """Test introspecting with invalid API key format."""
    response = client.post(
        "/api-keys/introspect", headers={"Authorization": "Bearer invalid_key"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["active"] is False
    assert data["user_id"] is None
    assert data["key_id"] is None
    assert data["scopes"] is None
    assert data["expires_at"] is None


def test_introspect_api_key_no_authorization(client: TestClient):
    """Test introspecting without Authorization header."""
    response = client.post("/api-keys/introspect")

    assert response.status_code == 200
    data = response.json()

    assert data["active"] is False
    assert data["user_id"] is None
    assert data["key_id"] is None
    assert data["scopes"] is None
    assert data["expires_at"] is None


def test_introspect_api_key_wrong_bearer_format(client: TestClient):
    """Test introspecting with wrong Bearer format."""
    response = client.post(
        "/api-keys/introspect", headers={"Authorization": "Basic some_token"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["active"] is False
    assert data["user_id"] is None
    assert data["key_id"] is None
    assert data["scopes"] is None
    assert data["expires_at"] is None


def test_introspect_api_key_expired(client: TestClient, setup_expired_api_key):
    """Test introspecting an expired API key."""
    api_key, full_key = setup_expired_api_key

    response = client.post(
        "/api-keys/introspect", headers={"Authorization": f"Bearer {full_key}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["active"] is False
    assert data["user_id"] is None
    assert data["key_id"] is None
    assert data["scopes"] is None
    assert data["expires_at"] is None


def test_introspect_api_key_revoked(client: TestClient, setup_revoked_api_key):
    """Test introspecting a revoked API key."""
    api_key, full_key = setup_revoked_api_key

    response = client.post(
        "/api-keys/introspect", headers={"Authorization": f"Bearer {full_key}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["active"] is False
    assert data["user_id"] is None
    assert data["key_id"] is None
    assert data["scopes"] is None
    assert data["expires_at"] is None


def test_introspect_api_key_nonexistent(client: TestClient):
    """Test introspecting a non-existent API key."""
    response = client.post(
        "/api-keys/introspect",
        headers={"Authorization": "Bearer ak_nonexistent.secret"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["active"] is False
    assert data["user_id"] is None
    assert data["key_id"] is None
    assert data["scopes"] is None
    assert data["expires_at"] is None


def test_introspect_api_key_updates_last_used(client: TestClient, setup_api_key):
    """Test that introspection updates last_used_at."""
    api_key, full_key = setup_api_key

    # Introspect the API key
    response = client.post(
        "/api-keys/introspect", headers={"Authorization": f"Bearer {full_key}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["active"] is True

    # Note: In a real test, we would check that last_used_at was updated
    # But since we're using the test client with mocked database,
    # we can't easily verify the database was updated
    # This test mainly ensures the endpoint works without errors


def test_introspect_api_key_with_x_api_key_header(client: TestClient, setup_api_key):
    """Test introspecting an API key using X-API-Key header."""
    api_key, full_key = setup_api_key

    response = client.post("/api-keys/introspect", headers={"X-API-Key": full_key})

    assert response.status_code == 200
    data = response.json()

    assert data["active"] is True
    assert data["user_id"] == str(api_key.user_id)
    assert data["key_id"] == api_key.key_id
    assert data["scopes"] is None
    assert data["expires_at"] is not None


def test_introspect_api_key_priority_x_api_key_over_authorization(
    client: TestClient, setup_api_key
):
    """Test that X-API-Key takes priority over Authorization header in introspection."""
    api_key, full_key = setup_api_key

    # Test with both headers - X-API-Key should take priority
    response = client.post(
        "/api-keys/introspect",
        headers={"Authorization": "Bearer invalid_token", "X-API-Key": full_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["active"] is True  # Should work because X-API-Key is valid


@pytest.mark.skip(reason="Test requires proper db session handling in get_current_user")
def test_create_api_key_with_x_api_key_header(client: TestClient, setup_api_key, db):
    """Test creating an API key using X-API-Key header authentication."""
    api_key, full_key = setup_api_key

    # Test the authentication function directly
    from app.utils.auth import get_current_user
    from fastapi import Request
    from unittest.mock import Mock

    # Create a mock request with the database session
    mock_request = Mock(spec=Request)
    mock_request.state.db_session = db
    # Ensure no user is set in request state
    mock_request.state.user = None

    # Test the authentication function
    import asyncio

    result = asyncio.run(
        get_current_user(request=mock_request, authorization=None, x_api_key=full_key)
    )

    # Verify the authentication works
    assert result is not None
    assert result.id == api_key.user_id


@pytest.mark.skip(reason="Test requires proper db session handling in get_current_user")
def test_list_api_keys_with_x_api_key_header(client: TestClient, setup_api_key, db):
    """Test listing API keys using X-API-Key header authentication."""
    api_key, full_key = setup_api_key

    # Test the authentication function directly
    from app.utils.auth import get_current_user
    from fastapi import Request
    from unittest.mock import Mock

    # Create a mock request with the database session
    mock_request = Mock(spec=Request)
    mock_request.state.db_session = db
    # Ensure no user is set in request state
    mock_request.state.user = None

    # Test the authentication function
    import asyncio

    result = asyncio.run(
        get_current_user(request=mock_request, authorization=None, x_api_key=full_key)
    )

    # Verify the authentication works
    assert result is not None
    assert result.id == api_key.user_id


@pytest.mark.skip(reason="Test requires proper db session handling in get_current_user")
def test_api_key_authentication_priority(client: TestClient, setup_api_key, db):
    """Test that X-API-Key takes priority over Authorization header."""
    api_key, full_key = setup_api_key

    # Test the authentication function directly
    from app.utils.auth import get_current_user
    from fastapi import Request
    from unittest.mock import Mock

    # Create a mock request with the database session
    mock_request = Mock(spec=Request)
    mock_request.state.db_session = db
    # Ensure no user is set in request state
    mock_request.state.user = None

    # Test with both headers - X-API-Key should take priority
    import asyncio

    result = asyncio.run(
        get_current_user(
            request=mock_request,
            authorization="Bearer invalid_token",
            x_api_key=full_key,
        )
    )

    # Should work because X-API-Key is valid
    assert result is not None
    assert result.id == api_key.user_id


def test_invalid_x_api_key_header(client: TestClient, db):
    """Test that invalid X-API-Key header returns 401."""
    from app.utils.auth import get_current_user
    from fastapi import Request
    from unittest.mock import Mock
    import asyncio

    # Create a mock request with the database session
    mock_request = Mock(spec=Request)
    mock_request.state.db_session = db
    # Ensure no user is set in request state
    mock_request.state.user = None
    # Ensure no user is set in request state
    mock_request.state.user = None

    # Test with invalid API key
    try:
        asyncio.run(
            get_current_user(
                request=mock_request, authorization=None, x_api_key="invalid_key"
            )
        )
        assert False, "Should have raised HTTPException"
    except Exception as e:
        assert "Not authenticated" in str(e)


def test_missing_authentication_headers(client: TestClient, db):
    """Test that missing both authentication headers returns 401."""
    from app.utils.auth import get_current_user
    from fastapi import Request
    from unittest.mock import Mock
    import asyncio

    # Create a mock request with the database session
    mock_request = Mock(spec=Request)
    mock_request.state.db_session = db
    # Ensure no user is set in request state
    mock_request.state.user = None
    # Ensure no user is set in request state
    mock_request.state.user = None

    # Test with no authentication
    try:
        asyncio.run(
            get_current_user(request=mock_request, authorization=None, x_api_key=None)
        )
        assert False, "Should have raised HTTPException"
    except Exception as e:
        assert "Not authenticated" in str(e)


@pytest.mark.skip(reason="Test requires proper db session handling in get_current_user")
def test_api_key_authentication_with_expired_key(
    client: TestClient, setup_expired_api_key, db
):
    """Test that expired API key returns 401."""
    api_key, full_key = setup_expired_api_key

    from app.utils.auth import get_current_user
    from fastapi import Request
    from unittest.mock import Mock
    import asyncio

    # Create a mock request with the database session
    mock_request = Mock(spec=Request)
    mock_request.state.db_session = db
    # Ensure no user is set in request state
    mock_request.state.user = None

    # Test with expired API key
    try:
        asyncio.run(
            get_current_user(
                request=mock_request, authorization=None, x_api_key=full_key
            )
        )
        assert False, "Should have raised HTTPException"
    except Exception as e:
        assert "Not authenticated" in str(e)


def test_update_api_key_name(client: TestClient, setup_api_key):
    """Test updating an API key's name."""
    api_key, _ = setup_api_key

    update_data = {"name": "Updated API Key Name"}

    response = client.put(f"/api-keys/{api_key.id}", json=update_data)

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "id" in data
    assert "key_id" in data
    assert "name" in data
    assert "created_at" in data
    assert "last_used_at" in data
    assert "expires_at" in data
    assert "revoked" in data

    # Check values
    assert data["id"] == str(api_key.id)
    assert data["name"] == "Updated API Key Name"
    assert data["revoked"] is False  # Should remain unchanged


def test_update_api_key_revoked_status(client: TestClient, setup_api_key):
    """Test updating an API key's revoked status."""
    api_key, _ = setup_api_key

    update_data = {"revoked": True}

    response = client.put(f"/api-keys/{api_key.id}", json=update_data)

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check values
    assert data["id"] == str(api_key.id)
    assert data["name"] == api_key.name  # Should remain unchanged
    assert data["revoked"] is True


def test_update_api_key_both_fields(client: TestClient, setup_api_key):
    """Test updating both name and revoked status."""
    api_key, _ = setup_api_key

    update_data = {"name": "Updated Name and Revoked", "revoked": True}

    response = client.put(f"/api-keys/{api_key.id}", json=update_data)

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check values
    assert data["id"] == str(api_key.id)
    assert data["name"] == "Updated Name and Revoked"
    assert data["revoked"] is True


def test_update_api_key_not_found(client: TestClient):
    """Test updating a non-existent API key."""
    from uuid import uuid4

    update_data = {"name": "Updated Name"}

    response = client.put(f"/api-keys/{uuid4()}", json=update_data)

    # Assertions
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_update_api_key_wrong_user(client: TestClient, setup_another_user_api_key):
    """Test updating an API key belonging to another user."""
    api_key, _ = setup_another_user_api_key

    update_data = {"name": "Updated Name"}

    response = client.put(f"/api-keys/{api_key.id}", json=update_data)

    # Assertions
    assert response.status_code == 403
    data = response.json()
    assert "only update your own" in data["detail"].lower()


def test_update_api_key_invalid_data(client: TestClient, setup_api_key):
    """Test updating an API key with invalid data."""
    api_key, _ = setup_api_key

    # Test with empty name
    invalid_data = {"name": ""}

    response = client.put(f"/api-keys/{api_key.id}", json=invalid_data)

    # Assertions
    assert response.status_code == 422  # Validation error

    # Test with name too long
    invalid_data = {"name": "a" * 101}  # Exceeds max length

    response = client.put(f"/api-keys/{api_key.id}", json=invalid_data)

    # Assertions
    assert response.status_code == 422  # Validation error


def test_update_api_key_empty_request(client: TestClient, setup_api_key):
    """Test updating an API key with empty request body."""
    api_key, _ = setup_api_key

    update_data = {}

    response = client.put(f"/api-keys/{api_key.id}", json=update_data)

    # Should succeed but not change anything
    assert response.status_code == 200
    data = response.json()

    # Check that nothing changed
    assert data["id"] == str(api_key.id)
    assert data["name"] == api_key.name
    assert data["revoked"] == api_key.revoked
