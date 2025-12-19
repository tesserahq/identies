import pytest
from app.models.user import User


@pytest.fixture(scope="function")
def setup_system_account(db, faker):
    """Create a test system account for use in tests."""
    email = faker.email()

    user_data = {
        "email": email,
        "username": faker.user_name(),
        "first_name": faker.first_name(),
        "last_name": faker.last_name(),
        "external_id": f"system-{faker.uuid4()}",
        "service_account": True,
    }

    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@pytest.fixture(scope="function")
def setup_another_system_account(db, faker):
    """Create another test system account for use in tests."""
    email = faker.email()

    user_data = {
        "email": email,
        "username": faker.user_name(),
        "first_name": faker.first_name(),
        "last_name": faker.last_name(),
        "external_id": f"system-{faker.uuid4()}",
        "service_account": True,
    }

    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)

    return user
