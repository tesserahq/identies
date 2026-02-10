from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse
from fastapi import status

from app.middleware.auth.token_handler import TokenHandler

# from tessera_sdk.auth.token_handler import TokenHandler

from typing import Any, Optional
from tessera_sdk.core.database_manager import DatabaseManager
from app.middleware.auth.user_handler import UserHandler
from app.config import get_settings
from app.middleware.auth.exceptions import UnauthorizedException

SKIP_AUTH_PATHS = [
    "/health",
    "/openapi.json",
    "/docs",
    "/api-keys/introspect",
    "/metrics",
    "/.well-known/jwks.json",
]

M2M_AUTH_PATHS = [
    "/internal/users",
    "/oauth/token-exchange",
]

X_API_KEY_HEADER = "X-API-Key"


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        database_manager: Optional[DatabaseManager] = None,
    ):
        super().__init__(app)
        # Store database manager for creating sessions
        self.database_manager = database_manager
        self.config = get_settings()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in SKIP_AUTH_PATHS:
            return await call_next(request)

        # Check for X-API-Key header first
        x_api_key = request.headers.get(X_API_KEY_HEADER)
        if x_api_key:
            # TODO: This is wrong, we should not let the endpoint handle X-API-Key authentication
            # Let the endpoint handle X-API-Key authentication
            return await call_next(request)

        # Check for Authorization Bearer header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401, content={"error": "Missing or invalid token"}
            )

        token = authorization[len("Bearer ") :]

        if self.database_manager is None:
            return JSONResponse(
                status_code=500,
                content={"error": "Server authentication misconfigured"},
            )

        token_handler = TokenHandler()

        try:
            payload = token_handler.verify(token)
        except UnauthorizedException:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Unauthorized"},
            )

        request.state.jwt_payload = payload

        if any(request.url.path.startswith(path) for path in M2M_AUTH_PATHS):
            if self._is_allowed_service_account_for_m2m(payload):
                return await call_next(request)

            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden"},
            )

        user_handler = UserHandler(self.database_manager)
        request.state.jwt_payload = payload
        request.state.user = user_handler.resolve_user(token, payload)

        return await call_next(request)

    def _is_allowed_service_account_for_m2m(self, payload: dict[str, Any]) -> bool:
        account_type = payload.get(self.config.service_account_account_type_claim)
        is_service_account = (
            isinstance(account_type, str)
            and account_type.lower() == self.config.service_account_account_type_value
        )

        client_id = payload.get(self.config.service_account_client_id_claim)
        is_service_account_client_id = (
            isinstance(client_id, str)
            and client_id in self.config.get_allowed_service_account_client_ids()
        )

        return is_service_account and is_service_account_client_id
