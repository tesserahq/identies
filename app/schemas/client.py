from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    owner_id: UUID
    created_by_id: UUID

    model_config = ConfigDict(from_attributes=True)


class ClientCreate(ClientBase):
    pass


class ClientResponse(ClientBase):
    id: UUID
    client_id: str
    revoked: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientCreateResponse(ClientResponse):
    client_secret: str
    """The client secret — shown only once at creation."""


class ClientCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class OAuthTokenRequest(BaseModel):
    grant_type: str = Field(..., description="Must be 'client_credentials'")
    client_id: str
    client_secret: str
    audience: str


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
