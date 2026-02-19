from app.config import get_settings
from app.middleware.auth.exceptions import (
    UnauthorizedException,
    InviteOnlyAccessException,
)
from app.services.user_service import UserService
from app.services.access_rule_service import AccessRuleService
from app.commands.users.onboard_user_command import OnboardUserCommand
from app.schemas.user import User, UserOnboard
import requests
from datetime import datetime
from app.utils.db.db_session_helper import db_session


class UserHandler:
    """Handles user resolution from a validated JWT payload."""

    def __init__(self):
        self.config = get_settings()
        if self.config.oidc_domain is None:
            raise ValueError("oidc domain is not set in the configuration.")

    def resolve_user(self, token: str, payload: dict):
        """Resolve the local user from a validated JWT payload.

        - If the user exists locally, return it.
        - If the user does not exist:
          - For service accounts, onboard without calling userinfo.
          - For normal users, fetch userinfo and onboard.
        """
        user_id = payload["sub"]

        user = None
        with db_session() as db:
            user_service = UserService(db)
            user = user_service.get_user_by_id_or_external_id(user_id)
            if user:
                return User.model_validate(user)

        # Check if this is a service account (Auth0 M2M tokens include a custom claim)
        account_type = payload.get(self.config.service_account_account_type_claim)
        is_service_account = (
            isinstance(account_type, str)
            and account_type.lower() == self.config.service_account_account_type_value
        )

        if is_service_account:
            return self.handle_service_account_onboarding(payload)

        userinfo = self.fetch_user_info_from_oidc(token)
        return self.handle_user_onboarding(payload, userinfo)

    def fetch_user_info_from_oidc(self, access_token: str) -> dict:
        """Fetch user information from the oidc userinfo endpoint."""
        userinfo_url = f"https://{self.config.oidc_domain}/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(userinfo_url, headers=headers)

        if response.status_code != 200:
            raise UnauthorizedException(
                f"Failed to fetch user info from oidc. "
                f"Status code: {response.status_code}, Response: {response.text}"
            )

        return response.json()

    def handle_user_onboarding(self, payload: dict, userinfo: dict):
        """Onboard the user locally using the userinfo data."""
        if self.config.invite_only_access:
            with db_session() as db:
                access_rule_service = AccessRuleService(db)
                email = userinfo.get("email")
                if email and isinstance(email, str):
                    access_rule = access_rule_service.evaluate_email_access(email)
                    if not access_rule:
                        raise InviteOnlyAccessException(email=email)
                else:
                    raise InviteOnlyAccessException()

        user_id = payload["sub"]
        email = userinfo.get("email")
        name = userinfo.get("name", "Unkown Unkown").split(" ")
        first_name = name[0]
        last_name = name[1]
        avatar_url = userinfo.get("picture")

        # Extract identity information from JWT payload
        provider = None
        if "identies" in payload and payload["identies"]:
            # Get the first identity (users typically have just one)
            identity = payload["identies"][0]
            provider = identity.get("provider")

        # Onboard the user locally
        with db_session() as db:
            onboard_command = OnboardUserCommand(db)
            user = onboard_command.execute(
                UserOnboard(
                    external_id=user_id,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    avatar_url=avatar_url,
                    provider=provider,
                    verified=True,
                    verified_at=datetime.now(),
                )
            )
            return User.model_validate(user)

    def handle_service_account_onboarding(self, payload: dict):
        """Onboard a service account with generic values."""
        user_id = payload["sub"]

        # Authorized party (the party to which this token was issued)
        azp = payload["azp"]

        email = azp + "@" + self.config.oidc_domain

        # Onboard the service account with generic values
        with db_session() as db:
            onboard_command = OnboardUserCommand(db)
            user = onboard_command.execute(
                UserOnboard(
                    external_id=user_id,
                    email=email,  # Service accounts don't have emails
                    first_name="System",
                    last_name="Account",
                    avatar_url=None,  # No avatar for service accounts
                    provider=None,
                    verified=True,
                    verified_at=datetime.now(),
                    service_account=True,  # Mark as service account
                )
            )
            return User.model_validate(user)
