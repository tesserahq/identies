import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timezone, timedelta


@pytest.fixture
def service_account_create_data(faker):
    """Create sample system account creation data for testing."""
    return {
        "email": faker.email(),
        "first_name": faker.first_name(),
        "last_name": faker.last_name(),
    }


@pytest.fixture
def test_create_service_account(client: TestClient, service_account_create_data):
    """Test creating a new system account."""
    response = client.post("/service-accounts", json=service_account_create_data)

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "id" in data
    assert "email" in data
    assert "first_name" in data
    assert "last_name" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Check values
    assert data["email"] == service_account_create_data["email"]
    assert data["first_name"] == service_account_create_data["first_name"]
    assert data["last_name"] == service_account_create_data["last_name"]


def test_create_service_account_invalid_data(client: TestClient):
    """Test creating a system account with invalid data."""
    invalid_data = {
        "email": "invalid-email",  # Invalid email format
        "first_name": "",  # Empty first name should fail validation
        "last_name": "Test",
    }

    response = client.post("/service-accounts", json=invalid_data)

    # Assertions
    assert response.status_code == 422  # Validation error


def test_create_service_account_duplicate_email(client: TestClient, setup_user, faker):
    """Test creating a system account with duplicate email fails."""
    invalid_data = {
        "email": setup_user.email,  # Use existing user's email
        "first_name": faker.first_name(),
        "last_name": faker.last_name(),
    }

    response = client.post("/service-accounts", json=invalid_data)

    # Assertions
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_list_service_accounts_empty(client: TestClient):
    """Test listing system accounts when none exist."""
    response = client.get("/service-accounts")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure (fastapi-pagination Page format)
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data
    assert isinstance(data["items"], list)
    assert data["total"] == 0


def test_list_service_accounts_with_data(client: TestClient, setup_service_account):
    """Test listing system accounts when some exist."""
    response = client.get("/service-accounts")

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

    # Check that returned accounts are system accounts
    for account in data["items"]:
        assert "id" in account
        assert "email" in account
        assert "first_name" in account
        assert "last_name" in account


def test_list_service_accounts_pagination(client: TestClient, setup_service_account):
    """Test listing system accounts with pagination."""
    response = client.get("/service-accounts?page=1&size=10")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "page" in data
    assert "size" in data
    assert data["page"] == 1
    assert data["size"] == 10
    assert len(data["items"]) <= 10


def test_get_service_account(client: TestClient, setup_service_account):
    """Test getting a specific system account by ID."""
    response = client.get(f"/service-accounts/{setup_service_account.id}")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "id" in data
    assert "email" in data
    assert "first_name" in data
    assert "last_name" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Check values
    assert data["id"] == str(setup_service_account.id)
    assert data["email"] == setup_service_account.email
    assert data["first_name"] == setup_service_account.first_name
    assert data["last_name"] == setup_service_account.last_name


def test_get_service_account_not_found(client: TestClient):
    """Test getting a non-existent system account."""
    response = client.get(f"/service-accounts/{uuid4()}")

    # Assertions
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_service_account_not_service_account(client: TestClient, setup_user):
    """Test getting a regular user (not a service account) returns 404."""
    response = client.get(f"/service-accounts/{setup_user.id}")

    # Assertions
    assert response.status_code == 404
    data = response.json()
    assert "not a service account" in data["detail"].lower()


def test_update_service_account(client: TestClient, setup_service_account, faker):
    """Test updating a system account."""
    update_data = {
        "first_name": "Updated First",
        "last_name": "Updated Last",
        "email": faker.email(),
    }

    response = client.put(
        f"/service-accounts/{setup_service_account.id}", json=update_data
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "id" in data
    assert "email" in data
    assert "first_name" in data
    assert "last_name" in data

    # Check values
    assert data["id"] == str(setup_service_account.id)
    assert data["first_name"] == "Updated First"
    assert data["last_name"] == "Updated Last"
    assert data["email"] == update_data["email"]

    # Verify the account was actually updated by fetching again
    get_response = client.get(f"/service-accounts/{setup_service_account.id}")
    assert get_response.status_code == 200
    updated_data = get_response.json()
    assert updated_data["first_name"] == "Updated First"
    assert updated_data["last_name"] == "Updated Last"


def test_update_service_account_partial(client: TestClient, setup_service_account):
    """Test partially updating a system account."""
    original_email = setup_service_account.email
    original_last_name = setup_service_account.last_name

    update_data = {
        "first_name": "Updated First Only",
    }

    response = client.put(
        f"/service-accounts/{setup_service_account.id}", json=update_data
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check values
    assert data["first_name"] == "Updated First Only"
    assert data["email"] == original_email  # Should remain unchanged
    assert data["last_name"] == original_last_name  # Should remain unchanged


def test_update_service_account_not_found(client: TestClient, faker):
    """Test updating a non-existent system account."""
    update_data = {
        "first_name": "Updated First",
    }

    response = client.put(f"/service-accounts/{uuid4()}", json=update_data)

    # Assertions
    assert response.status_code == 400
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_update_service_account_not_service_account(
    client: TestClient, setup_user, faker
):
    """Test updating a regular user (not a service account) fails."""
    update_data = {
        "first_name": "Updated First",
    }

    response = client.put(f"/service-accounts/{setup_user.id}", json=update_data)

    # Assertions
    assert response.status_code == 400
    data = response.json()
    assert "not a service account" in data["detail"].lower()


def test_update_service_account_duplicate_email(
    client: TestClient, setup_service_account, setup_user
):
    """Test updating system account with duplicate email fails."""
    update_data = {
        "email": setup_user.email,  # Use existing user's email
    }

    response = client.put(
        f"/service-accounts/{setup_service_account.id}", json=update_data
    )

    # Assertions
    assert response.status_code == 400
    data = response.json()
    assert "already exists" in data["detail"].lower()


def test_delete_service_account(client: TestClient, setup_service_account):
    """Test deleting a system account."""
    account_id = setup_service_account.id

    response = client.delete(f"/service-accounts/{account_id}")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Service account deleted successfully"

    # Verify the account was actually deleted
    get_response = client.get(f"/service-accounts/{account_id}")
    assert get_response.status_code == 404


def test_delete_service_account_not_found(client: TestClient):
    """Test deleting a non-existent system account."""
    response = client.delete(f"/service-accounts/{uuid4()}")

    # Assertions
    assert response.status_code == 400
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_delete_service_account_not_service_account(client: TestClient, setup_user):
    """Test deleting a regular user (not a service account) fails."""
    response = client.delete(f"/service-accounts/{setup_user.id}")

    # Assertions
    assert response.status_code == 400
    data = response.json()
    assert "not a service account" in data["detail"].lower()


def test_service_account_validation(client: TestClient):
    """Test system account validation with various invalid inputs."""
    # Test with missing required fields
    invalid_data = {
        "email": "test@example.com",
        # Missing first_name and last_name
    }

    response = client.post("/service-accounts", json=invalid_data)
    assert response.status_code == 422

    # Test with empty first_name
    invalid_data = {
        "email": "test@example.com",
        "first_name": "",
        "last_name": "Test",
    }

    response = client.post("/service-accounts", json=invalid_data)
    assert response.status_code == 422

    # Test with empty last_name
    invalid_data = {
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "",
    }

    response = client.post("/service-accounts", json=invalid_data)
    assert response.status_code == 422


# Tests for GET /service-accounts/{service_account_id}/api-keys
def test_list_service_account_api_keys_success(
    client, setup_service_account, db, faker
):
    """Test listing API keys for a specific system account."""
    from app.models.api_key import ApiKey
    from app.utils.security import generate_api_key, hash_secret, parse_api_key

    # Create an API key for the system account
    full_key, key_id = generate_api_key()
    key_id_part, secret_part = parse_api_key(full_key)

    api_key_data = {
        "user_id": setup_service_account.id,
        "key_id": key_id_part,
        "secret_hash": hash_secret(secret_part),
        "name": faker.word(),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
    }

    api_key = ApiKey(**api_key_data)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    response = client.get(f"/service-accounts/{setup_service_account.id}/api-keys")

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


def test_list_service_account_api_keys_empty(client, setup_service_account):
    """Test listing API keys for a system account with no API keys."""
    response = client.get(f"/service-accounts/{setup_service_account.id}/api-keys")

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


def test_list_service_account_api_keys_not_found(client):
    """Test listing API keys for a non-existent system account."""
    response = client.get(f"/service-accounts/{uuid4()}/api-keys")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_list_service_account_api_keys_not_service_account(client, setup_user):
    """Test listing API keys for a regular user (not a service account)."""
    response = client.get(f"/service-accounts/{setup_user.id}/api-keys")

    assert response.status_code == 404
    data = response.json()
    assert "not a service account" in data["detail"].lower()


def test_list_service_account_api_keys_multiple_keys(
    client, setup_service_account, db, faker
):
    """Test listing API keys when system account has multiple keys."""
    from app.models.api_key import ApiKey
    from app.utils.security import generate_api_key, hash_secret, parse_api_key

    # Create multiple API keys for the system account
    for i in range(3):
        full_key, key_id = generate_api_key()
        key_id_part, secret_part = parse_api_key(full_key)

        api_key_data = {
            "user_id": setup_service_account.id,
            "key_id": key_id_part,
            "secret_hash": hash_secret(secret_part),
            "name": f"Test Key {i}",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
        }

        api_key = ApiKey(**api_key_data)
        db.add(api_key)

    db.commit()

    response = client.get(f"/service-accounts/{setup_service_account.id}/api-keys")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 3
    assert data["total"] >= 3


# Tests for POST /service-accounts/{service_account_id}/api-keys
@pytest.fixture
def service_account_api_key_create_data(faker):
    """Create sample API key creation data for testing."""
    return {
        "name": faker.word(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }


@pytest.fixture
def service_account_api_key_create_data_no_expiry(faker):
    """Create sample API key creation data without expiry for testing."""
    return {
        "name": faker.word(),
        "expires_at": None,
    }


def test_create_service_account_api_key_success(
    client, setup_service_account, service_account_api_key_create_data
):
    """Test creating a new API key for a specific system account."""
    response = client.post(
        f"/service-accounts/{setup_service_account.id}/api-keys",
        json=service_account_api_key_create_data,
    )

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
    assert data["name"] == service_account_api_key_create_data["name"]
    assert data["revoked"] is False
    assert data["full_key"].startswith("ak_")
    assert "." in data["full_key"]
    assert data["user_id"] == str(setup_service_account.id)


def test_create_service_account_api_key_no_expiry(
    client, setup_service_account, service_account_api_key_create_data_no_expiry
):
    """Test creating an API key for a system account without expiry."""
    response = client.post(
        f"/service-accounts/{setup_service_account.id}/api-keys",
        json=service_account_api_key_create_data_no_expiry,
    )

    assert response.status_code == 200
    data = response.json()

    # Check values
    assert data["name"] == service_account_api_key_create_data_no_expiry["name"]
    assert data["expires_at"] is None
    assert data["revoked"] is False
    assert data["user_id"] == str(setup_service_account.id)


def test_create_service_account_api_key_not_found(
    client, service_account_api_key_create_data
):
    """Test creating an API key for a non-existent system account."""
    response = client.post(
        f"/service-accounts/{uuid4()}/api-keys",
        json=service_account_api_key_create_data,
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_create_service_account_api_key_not_service_account(
    client, setup_user, service_account_api_key_create_data
):
    """Test creating an API key for a regular user (not a service account)."""
    response = client.post(
        f"/service-accounts/{setup_user.id}/api-keys",
        json=service_account_api_key_create_data,
    )

    assert response.status_code == 404
    data = response.json()
    assert "not a service account" in data["detail"].lower()


def test_create_service_account_api_key_invalid_data(client, setup_service_account):
    """Test creating an API key for a system account with invalid data."""
    invalid_data = {
        "name": "",  # Empty name should fail validation
    }

    response = client.post(
        f"/service-accounts/{setup_service_account.id}/api-keys", json=invalid_data
    )

    assert response.status_code == 422  # Validation error


def test_create_service_account_api_key_validation(client, setup_service_account):
    """Test API key validation with various invalid inputs."""
    # Test with missing name
    invalid_data = {
        "expires_at": None,
    }

    response = client.post(
        f"/service-accounts/{setup_service_account.id}/api-keys", json=invalid_data
    )
    assert response.status_code == 422

    # Test with name too long
    invalid_data = {
        "name": "a" * 101,  # Exceeds max length
        "expires_at": None,
    }

    response = client.post(
        f"/service-accounts/{setup_service_account.id}/api-keys", json=invalid_data
    )
    assert response.status_code == 422
