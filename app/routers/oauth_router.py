from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.repositories.client_credentials_repository import (
    ClientCredentialsRepository,
    ServiceAccountClientContext,
)
from app.repositories.client_repository import ClientRepository
from app.schemas.client import OAuthTokenRequest, OAuthTokenResponse
from app.core.logging_config import get_logger

# NOTE: This router is in SKIP_AUTH_PATHS — no bearer token is required.
# Clients authenticate by presenting their client_id + client_secret in the request body.
# Do NOT add RBAC or get_current_user dependencies here.
router = APIRouter(prefix="/oauth", tags=["OAuth"])

logger = get_logger()


@router.post("/token", response_model=OAuthTokenResponse, operation_id="oauth_token")
async def oauth_token(
    body: OAuthTokenRequest,
    db: Session = Depends(get_db),
):
    if body.grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported grant_type",
        )

    settings = get_settings()

    allowed_audiences = settings.get_token_exchange_audiences()
    if body.audience not in allowed_audiences:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audience",
        )

    client = ClientRepository(db).verify_client(body.client_id, body.client_secret)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
        )

    service_account_client = None
    if client.owner.service_account:
        service_account_client = ServiceAccountClientContext(
            client_id=client.client_id,
            client_name=client.name,
        )

    result = ClientCredentialsRepository(settings).mint_token(
        str(client.owner_id),
        body.audience,
        service_account_client=service_account_client,
    )

    return OAuthTokenResponse(
        access_token=result.access_token,
        expires_in=result.expires_in,
    )
