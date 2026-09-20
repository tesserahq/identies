import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.constants.user_kinds import UserKind
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.service_account import ServiceAccountOnboard
from app.schemas.user import UserCreate, UserOnboard, UserResponse


def test_human_created_through_repository_has_kind_human(db, faker):
    user = UserRepository(db).create_user(
        UserCreate(
            email=faker.email(),
            first_name=faker.first_name(),
            last_name=faker.last_name(),
        )
    )

    assert user.kind == "human"
    assert user.service_account is False


def test_onboarded_user_has_kind_human(db, faker):
    user = UserRepository(db).onboard_user(
        UserOnboard(
            email=faker.email(),
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            external_id=faker.uuid4(),
        )
    )

    assert user.kind == "human"


def test_onboarded_service_account_flag_yields_kind_service_account(db, faker):
    """The M2M onboarding path only sets the flag; kind must follow it."""
    user = UserRepository(db).onboard_user(
        UserOnboard(
            email=faker.email(),
            first_name="System",
            last_name="Account",
            external_id=faker.uuid4(),
            service_account=True,
        )
    )

    assert user.kind == "service_account"


def test_service_account_onboard_has_kind_service_account(db, faker):
    user = UserRepository(db).onboard_service_account(
        ServiceAccountOnboard(
            email=faker.email(),
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            external_id=f"system-{faker.uuid4()}",
        )
    )

    assert user.kind == "service_account"


def test_explicit_kind_is_kept(db, faker):
    user = User(
        email=faker.email(),
        first_name="Claude",
        last_name="Agent",
        service_account=True,
        kind=UserKind.AGENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.kind == "agent"


def test_unknown_kind_is_rejected_before_reaching_the_database():
    with pytest.raises(ValueError):
        User(email="a@example.com", first_name="A", last_name="B", kind="robot")


def test_database_rejects_a_missing_or_unknown_kind(db, setup_user):
    """The constraint is enforced by the database, not only by the model."""
    user_id = setup_user.id

    for statement in (
        "UPDATE users SET kind = NULL WHERE id = :id",
        "UPDATE users SET kind = 'robot' WHERE id = :id",
    ):
        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.execute(text(statement), {"id": user_id})


def test_user_response_exposes_kind(setup_user, setup_service_account):
    assert UserResponse.model_validate(setup_user).kind == UserKind.HUMAN
    assert (
        UserResponse.model_validate(setup_service_account).kind
        == UserKind.SERVICE_ACCOUNT
    )
