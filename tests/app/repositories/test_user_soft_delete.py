import pytest
from sqlalchemy.exc import IntegrityError

from app.commands.service_accounts.delete_service_account_command import (
    DeleteServiceAccountCommand,
)
from app.models.user import User
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate


def test_delete_user_keeps_the_row_and_hides_it_from_lookups(db, setup_user):
    repository = UserRepository(db)
    user_id, email, external_id = (
        setup_user.id,
        setup_user.email,
        setup_user.external_id,
    )

    assert repository.delete_user(user_id) is True

    assert repository.get_user(user_id) is None
    assert repository.get_user_by_email(email) is None
    assert repository.get_user_by_external_id(external_id) is None
    assert repository.get_user_by_id_or_external_id(str(user_id)) is None
    assert repository.get_user_by_id_or_external_id(external_id) is None
    assert user_id not in {u.id for u in repository.get_users()}
    assert user_id not in {u.id for u in repository.get_users_query().all()}
    assert user_id not in {u.id for u in repository.search({"email": email})}

    # The row itself is kept, so records that reference it still resolve.
    tombstone = repository.get_user(user_id, include_deleted=True)
    assert tombstone is not None
    assert tombstone.deleted_at is not None


def test_delete_user_twice_and_unknown_user(db, setup_user):
    repository = UserRepository(db)

    assert repository.delete_user(setup_user.id) is True
    assert repository.delete_user(setup_user.id) is False


def test_deleted_users_cannot_be_updated_or_verified(db, setup_user):
    repository = UserRepository(db)
    repository.delete_user(setup_user.id)

    assert repository.update_user(setup_user.id, UserUpdate(first_name="X")) is None
    assert repository.verify_user(setup_user.id) is None


def test_deleted_service_accounts_leave_service_account_lists(
    db, setup_service_account
):
    repository = UserRepository(db)
    repository.delete_user(setup_service_account.id)

    ids = {u.id for u in repository.get_service_accounts_query().all()}
    assert setup_service_account.id not in ids


def test_email_and_external_id_can_be_reused_after_delete(db, setup_user, faker):
    repository = UserRepository(db)
    email, external_id = setup_user.email, setup_user.external_id
    repository.delete_user(setup_user.id)

    replacement = User(
        email=email, first_name="New", last_name="Person", external_id=external_id
    )
    db.add(replacement)
    db.commit()

    assert repository.get_user_by_email(email).id == replacement.id


def test_active_users_still_cannot_share_an_email(db, setup_user):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(User(email=setup_user.email, first_name="Dup", last_name="User"))
            db.flush()


def test_delete_user_revokes_their_api_keys_and_clients(
    db, setup_service_account, faker
):
    from app.models.api_key import ApiKey
    from app.models.client import Client
    from app.utils.security import (
        generate_api_key,
        generate_client_credentials,
        hash_secret,
        parse_api_key,
    )

    full_key, _ = generate_api_key()
    key_id, secret = parse_api_key(full_key)
    api_key = ApiKey(
        user_id=setup_service_account.id,
        key_id=key_id,
        secret_hash=hash_secret(secret),
        name="k",
    )
    client_id, client_secret = generate_client_credentials()
    client = Client(
        client_id=client_id,
        secret_hash=hash_secret(client_secret),
        name="c",
        owner_id=setup_service_account.id,
        created_by_id=setup_service_account.id,
    )
    db.add_all([api_key, client])
    db.commit()
    assert ApiKeyRepository(db).verify_api_key(full_key) is not None
    assert ClientRepository(db).verify_client(client_id, client_secret) is not None

    UserRepository(db).delete_user(setup_service_account.id)
    db.refresh(api_key)
    db.refresh(client)

    assert api_key.revoked is True
    assert client.revoked is True
    assert ApiKeyRepository(db).verify_api_key(full_key) is None
    assert ClientRepository(db).verify_client(client_id, client_secret) is None


def test_api_key_of_a_deleted_user_is_rejected_even_if_not_revoked(
    db, setup_api_key, setup_user
):
    """Defense in depth: validation itself checks the user, not just the revoked flag."""
    api_key, full_key = setup_api_key
    assert ApiKeyRepository(db).verify_api_key(full_key) is not None

    from datetime import datetime, timezone

    setup_user.deleted_at = datetime.now(timezone.utc)
    db.commit()

    assert api_key.revoked is False
    assert ApiKeyRepository(db).verify_api_key(full_key) is None


def test_client_of_a_deleted_owner_is_rejected_even_if_not_revoked(
    db, setup_client, setup_user
):
    client, secret = setup_client
    assert ClientRepository(db).verify_client(client.client_id, secret) is not None

    from datetime import datetime, timezone

    setup_user.deleted_at = datetime.now(timezone.utc)
    db.commit()

    assert client.revoked is False
    assert ClientRepository(db).verify_client(client.client_id, secret) is None


def test_service_account_with_credentials_can_be_deleted(
    db, setup_service_account_client, setup_service_account
):
    """Hard delete used to fail on the api_keys/clients foreign keys."""
    assert DeleteServiceAccountCommand(db).execute(setup_service_account.id) is True

    assert UserRepository(db).get_user(setup_service_account.id) is None
