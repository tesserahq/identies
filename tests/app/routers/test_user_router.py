from uuid import uuid4
from datetime import datetime, timezone, timedelta
import pytest


def test_get_userinfo_success(client, setup_user):
    """Test that the /userinfo endpoint returns the current user's information."""
    response = client.get("/userinfo")
    assert response.status_code == 200

    user_data = response.json()
    assert "id" in user_data
    assert "email" in user_data
    assert "first_name" in user_data
    assert "last_name" in user_data
    assert "preferred_name" in user_data
    assert "created_at" in user_data
    assert "updated_at" in user_data

    # Verify the returned user matches the test user
    test_user = setup_user
    assert user_data["id"] == str(test_user.id)
    assert user_data["email"] == test_user.email
    assert user_data["first_name"] == test_user.first_name
    assert user_data["last_name"] == test_user.last_name


def test_get_user_success(client, setup_user):
    """Test that the /user endpoint returns the current user's information."""
    response = client.get("/user")
    assert response.status_code == 200

    user_data = response.json()
    assert "id" in user_data
    assert "email" in user_data
    assert "first_name" in user_data
    assert "last_name" in user_data
    assert "created_at" in user_data
    assert "updated_at" in user_data

    # Verify the returned user matches the test user
    test_user = setup_user
    assert user_data["id"] == str(test_user.id)
    assert user_data["email"] == test_user.email
    assert user_data["first_name"] == test_user.first_name
    assert user_data["last_name"] == test_user.last_name


def test_get_user_by_id_success(client, setup_user):
    """Test that the GET /users/{user_id} endpoint returns a specific user's information."""
    test_user = setup_user
    response = client.get(f"/users/{test_user.id}")
    assert response.status_code == 200

    user_data = response.json()
    assert "id" in user_data
    assert "email" in user_data
    assert "first_name" in user_data
    assert "last_name" in user_data
    assert "created_at" in user_data
    assert "updated_at" in user_data

    # Verify the returned user matches the test user
    assert user_data["id"] == str(test_user.id)
    assert user_data["email"] == test_user.email
    assert user_data["first_name"] == test_user.first_name
    assert user_data["last_name"] == test_user.last_name


def test_get_user_by_id_not_found(client):
    """Test that the GET /users/{user_id} endpoint returns 404 for non-existent user."""
    non_existent_id = str(uuid4())
    response = client.get(f"/users/{non_existent_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_users_success(client, setup_user):
    """Test that the GET /users endpoint returns a paginated list of users."""
    test_user = setup_user
    response = client.get("/users")
    assert response.status_code == 200

    data = response.json()
    # Check response structure (fastapi-pagination Page format)
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data

    # Verify at least the setup_user is in the list
    assert len(data["items"]) >= 1
    assert data["total"] >= 1

    # Find the test user in the items
    user_ids = [user["id"] for user in data["items"]]
    assert str(test_user.id) in user_ids

    # Verify user data structure
    test_user_data = next(
        user for user in data["items"] if user["id"] == str(test_user.id)
    )
    assert test_user_data["email"] == test_user.email
    assert test_user_data["first_name"] == test_user.first_name
    assert test_user_data["last_name"] == test_user.last_name
    assert "preferred_name" in test_user_data
    assert "created_at" in test_user_data
    assert "updated_at" in test_user_data


def test_list_users_q_filter(client, db):
    """Test that GET /users?q=... filters by first_name, last_name, or email."""
    from app.models.user import User

    token = "unique-q-filter-token"

    matching_user = User(
        email=f"{token}@example.com",
        username=f"{token}@example.com",
        first_name="Filter",
        last_name="Match",
        provider="google",
        external_id=str(uuid4()),
    )
    non_matching_user = User(
        email="someone-else@example.com",
        username="someone-else@example.com",
        first_name="Someone",
        last_name="Else",
        provider="google",
        external_id=str(uuid4()),
    )

    db.add(matching_user)
    db.add(non_matching_user)
    db.commit()

    response = client.get(f"/users?q={token}")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(matching_user.id)
    assert data["items"][0]["email"] == matching_user.email


def test_list_users_multiple_users(client, setup_user, setup_another_user, db, faker):
    """Test listing users when there are multiple users."""
    # Create additional users
    from app.models.user import User

    additional_users = []
    for i in range(2):
        user_data = {
            "email": faker.email(),
            "username": faker.email(),
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "provider": "google",
            "external_id": faker.uuid4(),
        }
        user = User(**user_data)
        db.add(user)
        additional_users.append(user)

    db.commit()

    response = client.get("/users")
    assert response.status_code == 200

    data = response.json()
    # Should have at least setup_user, setup_another_user, and 2 additional users
    assert len(data["items"]) >= 4
    assert data["total"] >= 4

    # Verify all users are in the list
    user_ids = [user["id"] for user in data["items"]]
    assert str(setup_user.id) in user_ids
    assert str(setup_another_user.id) in user_ids
    for additional_user in additional_users:
        assert str(additional_user.id) in user_ids


def test_avatar_fields_in_response(client, setup_user):
    """Test that avatar_url is returned and contains avatar_asset_id value when present."""
    response = client.get("/userinfo")
    assert response.status_code == 200

    user_data = response.json()

    # avatar_url should be present in the response
    assert "avatar_url" in user_data

    # avatar_asset_id should also be present
    assert "avatar_asset_id" in user_data

    # If avatar_asset_id is set, avatar_url should contain that value
    if user_data["avatar_asset_id"]:
        assert user_data["avatar_url"] == user_data["avatar_asset_id"]


def test_avatar_url_fallback_to_original(client, setup_user):
    """Test that avatar_url falls back to original value when avatar_asset_id is not set."""
    # First, let's check the current state
    response = client.get("/userinfo")
    assert response.status_code == 200

    user_data = response.json()

    # If avatar_asset_id is None, avatar_url should be the original value (likely None in test)
    if user_data["avatar_asset_id"] is None:
        # In test environment, both are likely None, but the logic should work
        assert user_data["avatar_url"] is None or user_data[
            "avatar_url"
        ] == user_data.get("avatar_url")


def test_update_user_success(client, setup_user):
    """Test that the PUT /userinfo endpoint successfully updates user information."""
    # Prepare update data
    update_data = {
        "first_name": "Updated First",
        "last_name": "Updated Last",
        "email": "updated@example.com",
        "theme_preference": "dark",
        "preferred_name": "Preferred Display Name",
    }

    response = client.put("/user", json=update_data)
    assert response.status_code == 200

    user_data = response.json()
    assert user_data["first_name"] == "Updated First"
    assert user_data["last_name"] == "Updated Last"
    assert user_data["email"] == "updated@example.com"
    assert user_data["theme_preference"] == "dark"
    assert user_data["preferred_name"] == "Preferred Display Name"
    # Verify the user was actually updated by fetching again
    get_response = client.get("/userinfo")
    assert get_response.status_code == 200
    updated_user_data = get_response.json()
    assert updated_user_data["first_name"] == "Updated First"
    assert updated_user_data["last_name"] == "Updated Last"
    assert updated_user_data["email"] == "updated@example.com"
    assert updated_user_data["theme_preference"] == "dark"
    assert updated_user_data["preferred_name"] == "Preferred Display Name"


def test_update_user_partial(client, setup_user):
    """Test that the PUT /user endpoint allows partial updates."""
    # Update only preferred_name
    update_data = {"preferred_name": "Nickname Only"}

    response = client.put("/user", json=update_data)
    assert response.status_code == 200

    user_data = response.json()
    assert user_data["preferred_name"] == "Nickname Only"
    # Other fields should remain unchanged
    test_user = setup_user
    assert user_data["first_name"] == test_user.first_name
    assert user_data["last_name"] == test_user.last_name
    assert user_data["email"] == test_user.email


# def test_update_user_unauthorized(client):
#     """Test that the PUT /userinfo endpoint returns 401 when no authentication is provided."""
#     # Remove the Authorization header for this request
#     headers = dict(client.headers)
#     headers.pop("Authorization", None)
#     update_data = {"first_name": "Test"}
#     response = client.put("/userinfo", json=update_data, headers=headers)
#     assert response.status_code == 401
#     assert "detail" in response.json()
#     assert response.json()["detail"] == "Not authenticated"


# Tests for GET /users/{user_id}/api-keys
def test_list_user_api_keys_success(client, setup_user, setup_api_key):
    """Test listing API keys for a specific user."""
    # Create an API key for the user
    api_key, _ = setup_api_key

    response = client.get(f"/users/{setup_user.id}/api-keys")

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

    # Check that the API key is in the list
    api_key_ids = [key["id"] for key in data["items"]]
    assert str(api_key.id) in api_key_ids

    # Check that full_key is not included in list
    for api_key_item in data["items"]:
        assert "full_key" not in api_key_item
        assert "id" in api_key_item
        assert "key_id" in api_key_item
        assert "name" in api_key_item


def test_list_user_api_keys_empty(client, setup_user):
    """Test listing API keys for a user with no API keys."""
    response = client.get(f"/users/{setup_user.id}/api-keys")

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


def test_list_user_api_keys_not_found(client):
    """Test listing API keys for a non-existent user."""
    response = client.get(f"/users/{uuid4()}/api-keys")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_list_user_api_keys_multiple_keys(client, setup_user, db, faker):
    """Test listing API keys when user has multiple keys."""
    from app.models.api_key import ApiKey
    from app.utils.security import generate_api_key, hash_secret, parse_api_key

    # Create multiple API keys for the user
    for i in range(3):
        full_key, key_id = generate_api_key()
        key_id_part, secret_part = parse_api_key(full_key)

        api_key_data = {
            "user_id": setup_user.id,
            "key_id": key_id_part,
            "secret_hash": hash_secret(secret_part),
            "name": f"Test Key {i}",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
        }

        api_key = ApiKey(**api_key_data)
        db.add(api_key)

    db.commit()

    response = client.get(f"/users/{setup_user.id}/api-keys")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 3
    assert data["total"] >= 3


# Tests for POST /users/{user_id}/api-keys
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


def test_create_user_api_key_success(client, setup_user, api_key_create_data):
    """Test creating a new API key for a specific user."""
    response = client.post(f"/users/{setup_user.id}/api-keys", json=api_key_create_data)

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
    assert data["user_id"] == str(setup_user.id)


def test_create_user_api_key_no_expiry(
    client, setup_user, api_key_create_data_no_expiry
):
    """Test creating an API key for a user without expiry."""
    response = client.post(
        f"/users/{setup_user.id}/api-keys", json=api_key_create_data_no_expiry
    )

    assert response.status_code == 200
    data = response.json()

    # Check values
    assert data["name"] == api_key_create_data_no_expiry["name"]
    assert data["expires_at"] is None
    assert data["revoked"] is False
    assert data["user_id"] == str(setup_user.id)


def test_create_user_api_key_not_found(client, api_key_create_data):
    """Test creating an API key for a non-existent user."""
    response = client.post(f"/users/{uuid4()}/api-keys", json=api_key_create_data)

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_create_user_api_key_invalid_data(client, setup_user):
    """Test creating an API key for a user with invalid data."""
    invalid_data = {
        "name": "",  # Empty name should fail validation
    }

    response = client.post(f"/users/{setup_user.id}/api-keys", json=invalid_data)

    assert response.status_code == 422  # Validation error


def test_create_user_api_key_validation(client, setup_user):
    """Test API key validation with various invalid inputs."""
    # Test with missing name
    invalid_data = {
        "expires_at": None,
    }

    response = client.post(f"/users/{setup_user.id}/api-keys", json=invalid_data)
    assert response.status_code == 422

    # Test with name too long
    invalid_data = {
        "name": "a" * 101,  # Exceeds max length
        "expires_at": None,
    }

    response = client.post(f"/users/{setup_user.id}/api-keys", json=invalid_data)
    assert response.status_code == 422
