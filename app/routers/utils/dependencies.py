from uuid import UUID
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.api_key import ApiKey
from app.models.application import Application
from app.models.client import Client
from app.models.user import User as UserModel
from app.schemas.user import User
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.user_repository import UserRepository
from fastapi import Request
from fastapi import status


def get_current_user(request: Request) -> User:
    # Check if user is already set (for backward compatibility with middleware)
    if hasattr(request.state, "user") and request.state.user is not None:
        return request.state.user

    # If we get here, no valid authentication was found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )


def get_api_key_by_id(
    key_id: UUID,
    db: Session = Depends(get_db),
) -> ApiKey:
    """FastAPI dependency to get an API key by ID.

    Args:
        key_id: The UUID of the API key to retrieve
        db: Database session dependency

    Returns:
        ApiKey: The retrieved API key

    Raises:
        HTTPException: If the API key is not found
    """
    api_key = ApiKeyRepository(db).get_api_key_by_id(key_id)
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    return api_key


def get_application_by_id(
    application_id: UUID,
    db: Session = Depends(get_db),
) -> Application:
    """FastAPI dependency to get an application by ID.

    Args:
        application_id: The UUID of the application to retrieve (from path).
        db: Database session dependency.

    Returns:
        Application: The retrieved application (ORM model).

    Raises:
        HTTPException: If the application is not found.
    """
    application = ApplicationRepository(db).get_application(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def get_user_by_id(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> UserModel:
    """FastAPI dependency to get a user by ID.

    Args:
        user_id: The UUID of the user to retrieve (from path).
        db: Database session dependency.

    Returns:
        UserModel: The retrieved user (ORM model, session remains open for request).

    Raises:
        HTTPException: If the user is not found.
    """
    user = UserRepository(db).get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_client_by_id(
    client_id: UUID,
    db: Session = Depends(get_db),
) -> Client:
    """FastAPI dependency to get a client by ID."""
    client = ClientRepository(db).get_client_by_id(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client
