from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.db import get_db
from app.utils.auth import get_current_user
from app.schemas.api_key import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeyIntrospectResponse,
    ApiKeyUpdateRequest,
)
from app.schemas.user import UserResponse
from app.services.api_key_service import ApiKeyService
from app.models.user import User

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post("", response_model=ApiKeyCreateResponse)
async def create_api_key(
    request: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key for the current user.

    Returns the new API key with the full key shown only once.
    """
    api_key_service = ApiKeyService(db)

    # Create the API key
    api_key, full_key = api_key_service.create_api_key(
        user_id=current_user.id, name=request.name, expires_at=request.expires_at
    )

    # Return the response with the full key
    response_data = ApiKeyResponse.model_validate(api_key)
    return ApiKeyCreateResponse(
        **response_data.model_dump(),
        full_key=full_key,
    )


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys for the current user.

    Returns a list of API keys (without the secret part).
    """
    api_key_service = ApiKeyService(db)
    api_keys = api_key_service.get_user_api_keys(current_user.id)

    return ApiKeyListResponse(
        data=[ApiKeyResponse.model_validate(key) for key in api_keys]
    )


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific API key by its ID.

    Only the owner of the API key can retrieve it.
    Returns the API key details (without the secret part).
    """
    api_key_service = ApiKeyService(db)

    # Verify the API key exists and belongs to the user
    api_key = api_key_service.get_api_key_by_id(key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own API keys",
        )

    return ApiKeyResponse.model_validate(api_key)


@router.put("/{key_id}/revoke")
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke an API key by its ID.

    Only the owner of the API key can revoke it.
    """
    api_key_service = ApiKeyService(db)

    # Verify the API key exists and belongs to the user
    api_key = api_key_service.get_api_key_by_id(key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only revoke your own API keys",
        )

    # Revoke the API key
    success = api_key_service.revoke_api_key(key_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    return {"message": "API key revoked successfully"}


@router.put("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: UUID,
    request: ApiKeyUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an API key by its ID.

    Only the owner of the API key can update it.
    Only name and revoked fields can be updated.
    """
    api_key_service = ApiKeyService(db)

    # Verify the API key exists and belongs to the user
    api_key = api_key_service.get_api_key_by_id(key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own API keys",
        )

    # Update the API key
    updated_api_key = api_key_service.update_api_key(
        key_id, current_user.id, name=request.name, revoked=request.revoked
    )

    if not updated_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    return ApiKeyResponse.model_validate(updated_api_key)


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete an API key by its ID.

    Only the owner of the API key can delete it.
    """
    api_key_service = ApiKeyService(db)

    # Verify the API key exists and belongs to the user
    api_key = api_key_service.get_api_key_by_id(key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own API keys",
        )

    # Delete the API key
    success = api_key_service.delete_api_key(key_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    return {"message": "API key deleted successfully"}


@router.post("/introspect", response_model=ApiKeyIntrospectResponse)
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
