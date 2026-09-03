from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse
from fastapi import status, HTTPException

from app.middleware.auth.token_handler import TokenHandler

# from tessera_sdk.auth.token_handler import TokenHandler

from typing import Any

from app.middleware.auth.user_handler import UserHandler
from app.config import get_settings
from app.middleware.auth.exceptions import UnauthorizedException
from app.core.logging_config import get_logger

SKIP_AUTH_PATHS = [
    "/livez",
    "/readyz",
    "/api-keys/introspect",
    "/metrics",
    "/.well-known/jwks.json",
    "/oauth/token",
]

M2M_AUTH_PATHS = [
    "/internal/users",
    "/oauth/token-exchange",
]

X_API_KEY_HEADER = "X-API-Key"

logger = get_logger()


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.config = get_settings()
        # Built once and reused across requests so the JWKS client's own
        # key cache (cache_jwk_set/lifespan) is actually effective, instead
        # of every request re-fetching the JWKS from the IDP.
        self.token_handler = TokenHandler()
        self.user_handler = UserHandler()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in SKIP_AUTH_PATHS:
            return await call_next(request)

        # Resolve token from X-API-Key or Authorization Bearer (same flow for both)
        token = request.headers.get(X_API_KEY_HEADER)
        if not token:
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                token = authorization[len("Bearer ") :]
        if not token:
            return JSONResponse(
                status_code=401, content={"error": "Missing or invalid token"}
            )

        try:
            # Token/JWKS verification does blocking network I/O; run it off
            # the event loop so a slow IDP doesn't stall other requests.
            payload = await run_in_threadpool(self.token_handler.verify, token)
        except UnauthorizedException as e:
            logger.error("UnauthorizedException: %s", e)
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

        try:
            # resolve_user may call out to the IDP's userinfo endpoint;
            # keep that blocking call off the event loop as well.
            request.state.user = await run_in_threadpool(
                self.user_handler.resolve_user, token, payload
            )
        except HTTPException as e:
            logger.error("%s: %s", type(e).__name__, e.detail)
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

        return await call_next(request)

    def _has_service_account_claims(self, payload: dict[str, Any]) -> bool:
        account_type = payload.get(self.config.service_account_account_type_claim)
        if not (
            isinstance(account_type, str)
            and account_type.lower()
            == self.config.service_account_account_type_value.lower()
        ):
            return False
        client_id = payload.get(self.config.service_account_client_id_claim)
        return isinstance(client_id, str) and bool(client_id)

    def _is_local_identies_token(self, payload: dict[str, Any]) -> bool:
        issuer = payload.get("iss")
        return isinstance(issuer, str) and issuer == self.config.token_exchange_issuer

    def _is_allowed_service_account_for_m2m(self, payload: dict[str, Any]) -> bool:
        if not self._has_service_account_claims(payload):
            return False
        if self._is_local_identies_token(payload):
            return True
        client_id = payload[self.config.service_account_client_id_claim]
        return client_id in self.config.get_allowed_service_account_client_ids()
