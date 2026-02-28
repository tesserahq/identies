"""Tests for application router."""

import pytest
from uuid import uuid4


def test_create_application(client, sample_application_data):
    """Test creating an application via API."""
    response = client.post("/applications/", json=sample_application_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_application_data["name"]
    assert data["url"] == sample_application_data["url"]
    assert data["logo"] == sample_application_data["logo"]
    assert data["description"] == sample_application_data["description"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_get_applications(client, sample_application_data):
    """Test getting list of applications."""
    create_response = client.post("/applications/", json=sample_application_data)
    assert create_response.status_code == 201

    response = client.get("/applications/")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1


def test_get_application_by_id(client, sample_application_data):
    """Test getting a specific application by ID."""
    create_response = client.post("/applications/", json=sample_application_data)
    assert create_response.status_code == 201
    application_id = create_response.json()["id"]

    response = client.get(f"/applications/{application_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == application_id
    assert data["name"] == sample_application_data["name"]
    assert data["url"] == sample_application_data["url"]


def test_get_application_not_found(client):
    """Test getting a non-existent application returns 404."""
    non_existent_id = str(uuid4())
    response = client.get(f"/applications/{non_existent_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_update_application(client, sample_application_data):
    """Test updating an application."""
    create_response = client.post("/applications/", json=sample_application_data)
    assert create_response.status_code == 201
    application_id = create_response.json()["id"]

    update_data = {
        "name": "Updated App",
        "url": "https://updated.com",
        "logo": "https://updated.com/logo.png",
        "description": "Updated description",
    }

    response = client.put(f"/applications/{application_id}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == application_id
    assert data["name"] == update_data["name"]
    assert data["url"] == update_data["url"]
    assert data["description"] == update_data["description"]


def test_update_application_partial(client, sample_application_data):
    """Test partial update of an application."""
    create_response = client.post("/applications/", json=sample_application_data)
    assert create_response.status_code == 201
    application_id = create_response.json()["id"]

    update_data = {"description": "Updated description only"}

    response = client.put(f"/applications/{application_id}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == application_id
    assert data["name"] == sample_application_data["name"]
    assert data["url"] == sample_application_data["url"]
    assert data["description"] == update_data["description"]


def test_delete_application(client, sample_application_data):
    """Test deleting an application."""
    create_response = client.post("/applications/", json=sample_application_data)
    assert create_response.status_code == 201
    application_id = create_response.json()["id"]

    response = client.delete(f"/applications/{application_id}")
    assert response.status_code == 204

    get_response = client.get(f"/applications/{application_id}")
    assert get_response.status_code == 404


def test_delete_application_not_found(client):
    """Test deleting a non-existent application returns 404."""
    non_existent_id = str(uuid4())
    response = client.delete(f"/applications/{non_existent_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_applications_batch(client, sample_application_data):
    """Test batch creating applications."""
    payload = {
        "applications": [
            {
                "name": "App 1",
                "url": "https://app1.com",
                "logo": "https://app1.com/logo.png",
            },
            {"name": "App 2", "url": "https://app2.com"},
        ]
    }

    response = client.post("/applications/batch", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 2
    assert data["items"][0]["name"] == "App 1"
    assert data["items"][0]["url"] == "https://app1.com"
    assert data["items"][0]["logo"] == "https://app1.com/logo.png"
    assert "id" in data["items"][0]
    assert data["items"][1]["name"] == "App 2"
    assert data["items"][1]["url"] == "https://app2.com"
    assert "id" in data["items"][1]


def test_list_applications_with_search_query(client, sample_application_data):
    """Test listing applications with search query."""
    create_response = client.post("/applications/", json=sample_application_data)
    assert create_response.status_code == 201

    name = sample_application_data["name"]
    response = client.get(f"/applications/?q={name}")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
