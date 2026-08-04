import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.exceptions.offboarding_error import OffboardingNotScheduledError
from app.exceptions.resource_not_found_error import ResourceNotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository


class CancelOffboardingCommand:
    """
    Command to cancel a user's pending offboarding.

    Only valid while offboarding is still scheduled (not yet executed) -
    nothing destructive has happened yet at that point, so cancelling is a
    trivial state clear.
    """

    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserRepository(db)
        self.logger = logging.getLogger(__name__)

    def execute(self, user_id: UUID) -> User:
        try:
            user = self.user_service.get_user(user_id)
            if not user:
                raise ResourceNotFoundError("User not found")

            if user.offboarding_scheduled_at is None:
                raise OffboardingNotScheduledError(
                    "User has no pending offboarding to cancel"
                )

            updated_user = self.user_service.cancel_offboarding(user_id)
            if not updated_user:
                raise ResourceNotFoundError("User not found")

            return updated_user

        except (ResourceNotFoundError, OffboardingNotScheduledError):
            raise
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to cancel offboarding: {str(e)}")
