import pytest
from app.main import app


def test_get_userinfo_success(client, setup_user):
    """Test that the /userinfo endpoint returns the current user's information."""
    response = client.get("/userinfo/")
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
