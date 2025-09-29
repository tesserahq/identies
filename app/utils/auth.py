from datetime import datetime
from app.schemas.user import UserOnboard
import jwt
import requests  # For making HTTP requests
from fastapi import HTTPException, status, Request, Header
from fastapi.security import HTTPBearer
from typing import Optional

from app.config import get_settings
from app.services.access_rule_service import AccessRuleService
from app.services.user_service import UserService
from app.services.api_key_service import ApiKeyService

security = HTTPBearer()


class InviteOnlyAccessException(HTTPException):
    def __init__(
        self, detail: str = "Invitation required to access this service.", **kwargs
    ):
        """Returns HTTP 403 with custom payload"""
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "title": "Access not granted",
                "detail": detail,
                "code": "INVITE_REQUIRED",
            },
        )


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str, **kwargs):
        """Returns HTTP 403"""
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UnauthenticatedException(HTTPException):
    def __init__(self):
        """Returns HTTP 401"""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Requires authentication"
        )


def get_db_from_request(request: Request):
    return request.state.db_session


def verify_token_dependency(request: Request, token: str):
    verifier = VerifyToken(get_db_from_request(request))
    user = verifier.verify(token)
    request.state.user = user


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
):
    """
    Get the current user with support for both JWT tokens and API keys.

    Supports:
    - Authorization: Bearer <jwt_token>
    - X-API-Key: <api_key>
    """
    db = get_db_from_request(request)

    # Try API key authentication first
    if x_api_key:
        api_key_service = ApiKeyService(db)
        api_key = api_key_service.verify_api_key(str(x_api_key))
        if api_key:
            request.state.user = api_key.user
            return api_key.user

    # Try Bearer token authentication
    if authorization and str(authorization).startswith("Bearer "):
        token = str(authorization)[7:]  # Remove "Bearer " prefix
        verifier = VerifyToken(db)
        try:
            user = verifier.verify(token)
            request.state.user = user
            return user
        except Exception:
            pass  # Continue to check if user is already set

    # Check if user is already set (for backward compatibility with middleware)
    if hasattr(request.state, "user") and request.state.user is not None:
        return request.state.user

    # If we get here, no valid authentication was found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )


class VerifyToken:
    """Does all the token verification using PyJWT"""

    def __init__(self, db_session):
        self.config = get_settings()
        self.db = db_session  # Store the DB session
        self.user_service = UserService(self.db)

        if self.config.oidc_domain is None:
            raise ValueError("oidc domain is not set in the configuration.")

        # This gets the JWKS from a given URL and does processing so you can
        # use any of the keys available
        jwks_url = f"https://{self.config.oidc_domain}/.well-known/jwks.json"
        self.jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True)

    def verify(self, token: str):
        if token is None:
            raise UnauthenticatedException

        # This gets the 'kid' from the passed token
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token).key
        except jwt.exceptions.PyJWKClientError as error:
            # raise UnauthorizedException(str(error))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
            )
        except jwt.exceptions.DecodeError as error:
            # raise UnauthorizedException(str(error))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
            )

        try:
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=self.config.oidc_algorithms,
                audience=self.config.oidc_api_audience,
                issuer=self.config.oidc_issuer,
            )
        except Exception as error:
            raise UnauthorizedException(str(error))

        # Extract user ID from JWT payload
        user_id = payload["sub"]

        # User not in cache or cache was invalid, check database
        user = self.user_service.get_user_by_external_id(user_id)

        if user:
            # User exists in database, cache the existence
            return user
        else:
            # Check if this is a service account (sub ends with @clients)
            is_service_account = user_id.endswith("@clients")

            if is_service_account:
                # Handle service account onboarding without calling userinfo
                user = self.handle_service_account_onboarding(payload)
            else:
                # User doesn't exist, cache the non-existence and fetch from OIDC
                userinfo = self.fetch_user_info_from_oidc(token)
                user = self.handle_user_onboarding(payload, userinfo)
            return user

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
            access_rule_service = AccessRuleService(self.db)
            email = userinfo.get("email")

            access_rule = access_rule_service.evaluate_email_access(email)
            if not access_rule:
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
        user = self.user_service.onboard_user(
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

        return user

    def handle_service_account_onboarding(self, payload: dict):
        """Onboard a service account with generic values."""
        user_id = payload["sub"]

        # Authorized party (the party to which this token was issued)
        azp = payload["azp"]

        email = azp + "@" + self.config.oidc_domain

        # Onboard the service account with generic values
        user = self.user_service.onboard_user(
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

        return user
