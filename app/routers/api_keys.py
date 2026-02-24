from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.commands.api_keys.update_api_key_command import UpdateApiKeyCommand
from app.commands.api_keys.delete_api_key_command import DeleteApiKeyCommand
from app.commands.api_keys.revoke_api_key_command import RevokeApiKeyCommand
from app.db import get_db
from app.routers.utils.dependencies import get_current_user
from app.routers.utils.dependencies import get_api_key_by_id
from app.schemas.api_key import (
    ApiKeyResponse,
    ApiKeyIntrospectResponse,
    ApiKeyUpdateRequest,
)
from app.schemas.user import UserResponse
from app.services.api_key_service import ApiKeyService
from app.models.user import User
from app.models.api_key import ApiKey
from app.auth.rbac import build_rbac_dependencies
from app.commands.api_keys.create_api_key_command import CreateApiKeyCommand
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreateRequest, ApiKeyCreateResponse
from app.services.user_service import UserService
from uuid import UUID

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


async def infer_domain(request: Request) -> Optional[str]:
    return "*"


RESOURCE = "api_key"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.get("/{key_id}", response_model=ApiKeyResponse, operation_id="get_api_key")
async def get_api_key(
    api_key: ApiKey = Depends(get_api_key_by_id),
    _current_user: User = Depends(get_current_user),
    _authorized: bool = Depends(rbac["read"]),
):
    """
    Get a specific API key by its ID.

    Only the owner of the API key can retrieve it.
    Returns the API key details (without the secret part).
    """
    return ApiKeyResponse.model_validate(api_key)


@router.put("/{key_id}/revoke", operation_id="revoke_api_key")
async def revoke_api_key(
    api_key: ApiKey = Depends(get_api_key_by_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke an API key by its ID.

    Only the owner of the API key can revoke it.
    """
    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only revoke your own API keys",
        )

    # Revoke the API key using the command
    revoke_api_key_command = RevokeApiKeyCommand(db)
    try:
        revoked_api_key = revoke_api_key_command.execute(
            api_key.id, current_user.id, current_user
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return {"message": "API key revoked successfully"}


@router.put("/{key_id}", response_model=ApiKeyResponse, operation_id="update_api_key")
async def update_api_key(
    api_key_update_request: ApiKeyUpdateRequest,
    api_key: ApiKey = Depends(get_api_key_by_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an API key by its ID.

    Only the owner of the API key can update it.
    Only name and revoked fields can be updated.
    """
    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own API keys",
        )

    # Update the API key using the command
    update_api_key_command = UpdateApiKeyCommand(db)
    try:
        updated_api_key = update_api_key_command.execute(
            api_key.id, current_user.id, api_key_update_request, current_user
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return ApiKeyResponse.model_validate(updated_api_key)


@router.delete(
    "/{key_id}", operation_id="delete_api_key", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_api_key(
    api_key: ApiKey = Depends(get_api_key_by_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete an API key by its ID.

    Only the owner of the API key can delete it.
    """
    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own API keys",
        )

    # Delete the API key using the command
    delete_api_key_command = DeleteApiKeyCommand(db)
    try:
        success = delete_api_key_command.execute(
            api_key.id, current_user.id, current_user
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# NOTE: Do NOT use RBAC dependencies here, as that will create a circular dependency with
# the authorization service Custos. This endpoint must always avoid any RBAC dependency!
@router.post(
    "/introspect",
    response_model=ApiKeyIntrospectResponse,
    operation_id="introspect_api_key",
)
async def introspect_api_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Introspect an API key to check if it's valid and get information about it.

    Input: API key via Authorization: Bearer ak_<id>.<secret> header or X-API-Key: ak_<id>.<secret>
    Output: JSON with active, user_id, key_id, scopes, expires_at

    Returns active: false if invalid, revoked, or expired.
    Updates last_used_at when valid.
    """
    api_key = None

    # Try X-API-Key header first
    if x_api_key:
        api_key = str(x_api_key)
    # Try Authorization header
    elif authorization and str(authorization).startswith("Bearer "):
        api_key = str(authorization)[7:]  # Remove "Bearer " prefix

    # If no API key found, return inactive
    if not api_key:
        return ApiKeyIntrospectResponse(active=False)

    # Verify the API key
    api_key_service = ApiKeyService(db)
    verified_api_key = api_key_service.verify_api_key(api_key)

    if not verified_api_key:
        return ApiKeyIntrospectResponse(active=False)

    # Return active API key information
    return ApiKeyIntrospectResponse(
        active=True,
        user_id=verified_api_key.user_id,
        user=(
            UserResponse.model_validate(verified_api_key.user)
            if verified_api_key.user
            else None
        ),
        key_id=verified_api_key.key_id,
        scopes=None,  # No scopes implemented yet
        expires_at=verified_api_key.expires_at,
    )


@router.post(
    "/users/{user_id}/api-keys",
    response_model=ApiKeyCreateResponse,
    operation_id="create_user_api_key",
)
async def create_user_api_key(
    user_id: UUID,
    api_key_data: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key for a specific user.

    Returns the new API key with the full key shown only once.
    """
    # Verify the user exists
    user_service = UserService(db)
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    create_api_key_command = CreateApiKeyCommand(db)

    # Create the API key
    api_key, full_key = create_api_key_command.execute(
        ApiKeyCreate(
            user_id=user_id,
            name=api_key_data.name,
            expires_at=api_key_data.expires_at,
        ),
        current_user,
    )

    # Return the response with the full key
    response_data = ApiKeyResponse.model_validate(api_key)
    return ApiKeyCreateResponse(
        **response_data.model_dump(),
        full_key=full_key,
    )
