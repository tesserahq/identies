from fastapi import HTTPException
from typing import Optional
from starlette import status


class InviteOnlyAccessException(HTTPException):
    def __init__(
        self,
        detail: str = "Invitation required to access this service.",
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        **kwargs,
    ):
        """Returns HTTP 403 with custom payload including user info if provided"""
        payload = {
            "title": "Access not granted",
            "detail": detail,
            "code": "INVITE_REQUIRED",
        }

        if email:
            payload["email"] = email
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name

        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=payload,
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
