import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.fixture
def system_account_create_data(faker):
    """Create sample system account creation data for testing."""
    return {
        "email": faker.email(),
        "first_name": faker.first_name(),
        "last_name": faker.last_name(),
        "username": faker.user_name(),
    }


@pytest.fixture
def system_account_create_data_no_username(faker):
    """Create sample system account creation data without username for testing."""
    return {
        "email": faker.email(),
        "first_name": faker.first_name(),
        "last_name": faker.last_name(),
    }


def test_create_system_account(client: TestClient, system_account_create_data):
    """Test creating a new system account."""
    response = client.post("/system-accounts", json=system_account_create_data)

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
    assert data["email"] == system_account_create_data["email"]
    assert data["first_name"] == system_account_create_data["first_name"]
    assert data["last_name"] == system_account_create_data["last_name"]
    assert data["username"] == system_account_create_data["username"]


def test_create_system_account_no_username(
    client: TestClient, system_account_create_data_no_username
):
    """Test creating a system account without username."""
    response = client.post(
        "/system-accounts", json=system_account_create_data_no_username
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check values
    assert data["email"] == system_account_create_data_no_username["email"]
    assert data["first_name"] == system_account_create_data_no_username["first_name"]
    assert data["last_name"] == system_account_create_data_no_username["last_name"]


def test_create_system_account_invalid_data(client: TestClient):
    """Test creating a system account with invalid data."""
    invalid_data = {
        "email": "invalid-email",  # Invalid email format
        "first_name": "",  # Empty first name should fail validation
        "last_name": "Test",
    }

    response = client.post("/system-accounts", json=invalid_data)

    # Assertions
    assert response.status_code == 422  # Validation error


def test_create_system_account_duplicate_email(client: TestClient, setup_user, faker):
    """Test creating a system account with duplicate email fails."""
    invalid_data = {
        "email": setup_user.email,  # Use existing user's email
        "first_name": faker.first_name(),
        "last_name": faker.last_name(),
    }

    response = client.post("/system-accounts", json=invalid_data)

    # Assertions
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_list_system_accounts_empty(client: TestClient):
    """Test listing system accounts when none exist."""
    response = client.get("/system-accounts")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "data" in data
    assert isinstance(data["data"], list)


def test_list_system_accounts_with_data(client: TestClient, setup_system_account):
    """Test listing system accounts when some exist."""
    response = client.get("/system-accounts")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "data" in data
    assert len(data["data"]) >= 1

    # Check that returned accounts are system accounts
    for account in data["data"]:
        assert "id" in account
        assert "email" in account
        assert "first_name" in account
        assert "last_name" in account


def test_list_system_accounts_pagination(client: TestClient, setup_system_account):
    """Test listing system accounts with pagination."""
    response = client.get("/system-accounts?skip=0&limit=10")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) <= 10


def test_get_system_account(client: TestClient, setup_system_account):
    """Test getting a specific system account by ID."""
    response = client.get(f"/system-accounts/{setup_system_account.id}")

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
    assert data["id"] == str(setup_system_account.id)
    assert data["email"] == setup_system_account.email
    assert data["first_name"] == setup_system_account.first_name
    assert data["last_name"] == setup_system_account.last_name


def test_get_system_account_not_found(client: TestClient):
    """Test getting a non-existent system account."""
    response = client.get(f"/system-accounts/{uuid4()}")

    # Assertions
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_system_account_not_service_account(client: TestClient, setup_user):
    """Test getting a regular user (not a system account) returns 404."""
    response = client.get(f"/system-accounts/{setup_user.id}")

    # Assertions
    assert response.status_code == 404
    data = response.json()
    assert "not a system account" in data["detail"].lower()


def test_update_system_account(client: TestClient, setup_system_account, faker):
    """Test updating a system account."""
    update_data = {
        "first_name": "Updated First",
        "last_name": "Updated Last",
        "email": faker.email(),
    }

    response = client.put(
        f"/system-accounts/{setup_system_account.id}", json=update_data
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
    assert data["id"] == str(setup_system_account.id)
    assert data["first_name"] == "Updated First"
    assert data["last_name"] == "Updated Last"
    assert data["email"] == update_data["email"]

    # Verify the account was actually updated by fetching again
    get_response = client.get(f"/system-accounts/{setup_system_account.id}")
    assert get_response.status_code == 200
    updated_data = get_response.json()
    assert updated_data["first_name"] == "Updated First"
    assert updated_data["last_name"] == "Updated Last"


def test_update_system_account_partial(client: TestClient, setup_system_account):
    """Test partially updating a system account."""
    original_email = setup_system_account.email
    original_last_name = setup_system_account.last_name

    update_data = {
        "first_name": "Updated First Only",
    }

    response = client.put(
        f"/system-accounts/{setup_system_account.id}", json=update_data
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Check values
    assert data["first_name"] == "Updated First Only"
    assert data["email"] == original_email  # Should remain unchanged
    assert data["last_name"] == original_last_name  # Should remain unchanged


def test_update_system_account_not_found(client: TestClient, faker):
    """Test updating a non-existent system account."""
    update_data = {
        "first_name": "Updated First",
    }

    response = client.put(f"/system-accounts/{uuid4()}", json=update_data)

    # Assertions
    assert response.status_code == 400
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_update_system_account_not_service_account(
    client: TestClient, setup_user, faker
):
    """Test updating a regular user (not a system account) fails."""
    update_data = {
        "first_name": "Updated First",
    }

    response = client.put(f"/system-accounts/{setup_user.id}", json=update_data)

    # Assertions
    assert response.status_code == 400
    data = response.json()
    assert "not a system account" in data["detail"].lower()


def test_update_system_account_duplicate_email(
    client: TestClient, setup_system_account, setup_user
):
    """Test updating system account with duplicate email fails."""
    update_data = {
        "email": setup_user.email,  # Use existing user's email
    }

    response = client.put(
        f"/system-accounts/{setup_system_account.id}", json=update_data
    )

    # Assertions
    assert response.status_code == 400
    data = response.json()
    assert "already exists" in data["detail"].lower()


def test_delete_system_account(client: TestClient, setup_system_account):
    """Test deleting a system account."""
    account_id = setup_system_account.id

    response = client.delete(f"/system-accounts/{account_id}")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "System account deleted successfully"

    # Verify the account was actually deleted
    get_response = client.get(f"/system-accounts/{account_id}")
    assert get_response.status_code == 404


def test_delete_system_account_not_found(client: TestClient):
    """Test deleting a non-existent system account."""
    response = client.delete(f"/system-accounts/{uuid4()}")

    # Assertions
    assert response.status_code == 400
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_delete_system_account_not_service_account(client: TestClient, setup_user):
    """Test deleting a regular user (not a system account) fails."""
    response = client.delete(f"/system-accounts/{setup_user.id}")

    # Assertions
    assert response.status_code == 400
    data = response.json()
    assert "not a system account" in data["detail"].lower()


def test_system_account_validation(client: TestClient):
    """Test system account validation with various invalid inputs."""
    # Test with missing required fields
    invalid_data = {
        "email": "test@example.com",
        # Missing first_name and last_name
    }

    response = client.post("/system-accounts", json=invalid_data)
    assert response.status_code == 422

    # Test with empty first_name
    invalid_data = {
        "email": "test@example.com",
        "first_name": "",
        "last_name": "Test",
    }

    response = client.post("/system-accounts", json=invalid_data)
    assert response.status_code == 422

    # Test with empty last_name
    invalid_data = {
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "",
    }

    response = client.post("/system-accounts", json=invalid_data)
    assert response.status_code == 422
