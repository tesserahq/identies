import pytest

from app.models.client import Client
from app.utils.security import generate_client_credentials, hash_secret


@pytest.fixture(scope="function")
def setup_client(db, setup_user, faker):
    """Create a test client for use in tests. Returns (Client, client_secret)."""
    client_id, client_secret = generate_client_credentials()

    client = Client(
        client_id=client_id,
        secret_hash=hash_secret(client_secret),
        name=faker.word(),
        owner_id=setup_user.id,
        created_by_id=setup_user.id,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    return client, client_secret


@pytest.fixture(scope="function")
def setup_service_account_client(db, setup_service_account, faker):
    """Create a test client owned by a service account. Returns (Client, client_secret)."""
    client_id, client_secret = generate_client_credentials()

    client = Client(
        client_id=client_id,
        secret_hash=hash_secret(client_secret),
        name=faker.word(),
        owner_id=setup_service_account.id,
        created_by_id=setup_service_account.id,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    return client, client_secret


@pytest.fixture(scope="function")
def setup_revoked_client(db, setup_user, faker):
    """Create a revoked test client."""
    client_id, client_secret = generate_client_credentials()

    client = Client(
        client_id=client_id,
        secret_hash=hash_secret(client_secret),
        name=faker.word(),
        owner_id=setup_user.id,
        created_by_id=setup_user.id,
        revoked=True,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    return client, client_secret
