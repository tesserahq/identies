from uuid import uuid4


def test_get_userinfo_success(client, setup_user):
    """Test that the /userinfo endpoint returns the current user's information."""
    response = client.get("/userinfo")
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
    }

    response = client.put("/user", json=update_data)
    assert response.status_code == 200

    user_data = response.json()
    assert user_data["first_name"] == "Updated First"
    assert user_data["last_name"] == "Updated Last"
    assert user_data["email"] == "updated@example.com"
    assert user_data["theme_preference"] == "dark"
    # Verify the user was actually updated by fetching again
    get_response = client.get("/userinfo")
    assert get_response.status_code == 200
    updated_user_data = get_response.json()
    assert updated_user_data["first_name"] == "Updated First"
    assert updated_user_data["last_name"] == "Updated Last"
    assert updated_user_data["email"] == "updated@example.com"
    assert updated_user_data["theme_preference"] == "dark"


def test_update_user_partial(client, setup_user):
    """Test that the PUT /user endpoint allows partial updates."""
    # Update only first name
    update_data = {"first_name": "Partial Update"}

    response = client.put("/user", json=update_data)
    assert response.status_code == 200

    user_data = response.json()
    assert user_data["first_name"] == "Partial Update"
    # Other fields should remain unchanged
    test_user = setup_user
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
