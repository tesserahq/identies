import uuid
import pytest


def test_create_user_client(client, setup_user, faker):
    response = client.post(
        f"/users/{setup_user.id}/clients", json={"name": faker.word()}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["client_id"].startswith("cs_")
    assert "client_secret" in data
    assert data["revoked"] is False
    assert data["owner_id"] == str(setup_user.id)


def test_list_user_clients(client, setup_user, setup_client):
    response = client.get(f"/users/{setup_user.id}/clients")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data
    assert len(data["items"]) >= 1
    assert data["total"] >= 1


def test_get_client(client, setup_client):
    db_client, _ = setup_client
    response = client.get(f"/clients/{db_client.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(db_client.id)


def test_get_client_not_found(client):
    response = client.get(f"/clients/{uuid.uuid4()}")
    assert response.status_code == 404


def test_revoke_client(client, setup_client):
    db_client, _ = setup_client
    response = client.put(f"/clients/{db_client.id}/revoke")
    assert response.status_code == 200
    assert response.json()["message"] == "Client revoked successfully"


def test_delete_client(client, setup_client):
    db_client, _ = setup_client
    response = client.delete(f"/clients/{db_client.id}")
    assert response.status_code == 204
    assert response.content == b""


def test_delete_client_not_found(client):
    response = client.delete(f"/clients/{uuid.uuid4()}")
    assert response.status_code == 404
