import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from app.schemas.access_rule import AccessRuleCreate


@pytest.fixture
def sample_access_rule_data():
    """Sample access rule data for testing."""
    return {
        "kind": "ip_whitelist",
        "value": "192.168.1.1",
        "note": "Test IP whitelist rule",
    }


def test_create_access_rule(client, sample_access_rule_data):
    """Test creating an access rule via API."""
    response = client.post("/access-rules/", json=sample_access_rule_data)

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == sample_access_rule_data["kind"]
    assert data["value"] == sample_access_rule_data["value"]
    assert data["note"] == sample_access_rule_data["note"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_access_rule_duplicate(client, sample_access_rule_data):
    """Test creating a duplicate access rule fails."""
    # Create first access rule
    response1 = client.post("/access-rules/", json=sample_access_rule_data)
    assert response1.status_code == 200

    # Try to create duplicate
    response2 = client.post("/access-rules/", json=sample_access_rule_data)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


def test_get_access_rules(client, sample_access_rule_data):
    """Test getting list of access rules."""
    # Create an access rule first
    create_response = client.post("/access-rules/", json=sample_access_rule_data)
    assert create_response.status_code == 200

    # Get all access rules
    response = client.get("/access-rules/")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1


def test_get_access_rule_by_id(client, sample_access_rule_data):
    """Test getting a specific access rule by ID."""
    # Create an access rule first
    create_response = client.post("/access-rules/", json=sample_access_rule_data)
    assert create_response.status_code == 200
    access_rule_id = create_response.json()["id"]

    # Get the access rule by ID
    response = client.get(f"/access-rules/{access_rule_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == access_rule_id
    assert data["kind"] == sample_access_rule_data["kind"]
    assert data["value"] == sample_access_rule_data["value"]


def test_get_access_rule_not_found(client):
    """Test getting a non-existent access rule returns 404."""
    non_existent_id = str(uuid4())
    response = client.get(f"/access-rules/{non_existent_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_update_access_rule(client, sample_access_rule_data):
    """Test updating an access rule."""
    # Create an access rule first
    create_response = client.post("/access-rules/", json=sample_access_rule_data)
    assert create_response.status_code == 200
    access_rule_id = create_response.json()["id"]

    # Update the access rule
    update_data = {
        "kind": "domain_restriction",
        "value": "updated.example.com",
        "note": "Updated test rule",
    }

    response = client.put(f"/access-rules/{access_rule_id}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == access_rule_id
    assert data["kind"] == update_data["kind"]
    assert data["value"] == update_data["value"]
    assert data["note"] == update_data["note"]


def test_update_access_rule_partial(client, sample_access_rule_data):
    """Test partial update of an access rule."""
    # Create an access rule first
    create_response = client.post("/access-rules/", json=sample_access_rule_data)
    assert create_response.status_code == 200
    access_rule_id = create_response.json()["id"]

    # Update only the note
    update_data = {"note": "Updated note only"}

    response = client.put(f"/access-rules/{access_rule_id}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == access_rule_id
    assert data["kind"] == sample_access_rule_data["kind"]  # Unchanged
    assert data["value"] == sample_access_rule_data["value"]  # Unchanged
    assert data["note"] == update_data["note"]  # Updated


def test_delete_access_rule(client, sample_access_rule_data):
    """Test deleting an access rule."""
    # Create an access rule first
    create_response = client.post("/access-rules/", json=sample_access_rule_data)
    assert create_response.status_code == 200
    access_rule_id = create_response.json()["id"]

    # Delete the access rule
    response = client.delete(f"/access-rules/{access_rule_id}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify it's deleted
    get_response = client.get(f"/access-rules/{access_rule_id}")
    assert get_response.status_code == 404


def test_delete_access_rule_not_found(client):
    """Test deleting a non-existent access rule returns 404."""
    non_existent_id = str(uuid4())
    response = client.delete(f"/access-rules/{non_existent_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_search_access_rules(client, sample_access_rule_data):
    """Test searching access rules."""
    # Create an access rule first
    create_response = client.post("/access-rules/", json=sample_access_rule_data)
    assert create_response.status_code == 200

    # Search by kind
    response = client.get("/access-rules/search/?kind=ip_whitelist")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1


def test_search_access_rules_by_note(client, sample_access_rule_data):
    """Test searching access rules by note content."""
    # Create an access rule first
    create_response = client.post("/access-rules/", json=sample_access_rule_data)
    assert create_response.status_code == 200

    # Search by note content
    response = client.get("/access-rules/search/?note=test")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1
