from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.utils.auth import verify_token_dependency, InviteOnlyAccessException


class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in [
            "/health",
            "/openapi.json",
            "/docs",
            "/api-keys/introspect",
        ]:
            return await call_next(request)

        # Check for X-API-Key header first
        x_api_key = request.headers.get("X-API-Key")
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

        try:
            # Now manually pass the raw token
            verify_token_dependency(request, token)
        except InviteOnlyAccessException as e:
            return JSONResponse(status_code=e.status_code, content=e.detail)
        except HTTPException as e:
            if e.status_code == status.HTTP_401_UNAUTHORIZED:
                return JSONResponse(status_code=401, content={"error": "Invsalid token aa aaa"})
            elif e.status_code == status.HTTP_403_FORBIDDEN:
                return JSONResponse(status_code=403, content={"error": "Forbidden 222"})

        return await call_next(request)
