from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TokenExchangeRequest(BaseModel):
    user_id: UUID = Field(description="Internal user id to act on behalf of.")
    requested_audience: str = Field(description="Target audience for the token.")
    requested_scope: str | list[str] = Field(
        description="Requested scopes (space-delimited string or list)."
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata for audit/logging.",
    )


class TokenExchangeResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
