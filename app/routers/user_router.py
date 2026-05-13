from fastapi import APIRouter, Depends, Request, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from typing import Optional

from app.auth.rbac import build_rbac_dependencies
from app.commands.clients.create_client_command import CreateClientCommand
from app.db import get_db
from app.models.user import User as UserModel
from app.repositories.client_repository import ClientRepository
from app.routers.utils.dependencies import get_current_user, get_user_by_id
from app.schemas.client import (
    ClientCreate,
    ClientCreateRequest,
    ClientCreateResponse,
    ClientResponse,
)
from app.schemas.user import UserResponse
from app.repositories.user_repository import UserRepository
from sqlalchemy.orm import Session

router = APIRouter(tags=["User"])


async def infer_domain(_request: Request) -> Optional[str]:
    return "*"


RESOURCE = "user"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.get(
    "/users/{user_id}", response_model=UserResponse, operation_id="get_user_by_id"
)
async def read_user(
    user: UserModel = Depends(get_user_by_id),
    _authorized: bool = Depends(rbac["read"]),
):
    """
    Get a specific user by ID.

    Returns the user with the specified ID, or 404 if not found.
    """
    return user


@router.get(
    "/internal/users/{user_id}",
    response_model=UserResponse,
    operation_id="get_user_by_id",
)
async def read_internal_user(
    user: UserModel = Depends(get_user_by_id),
):
    """
    Get a specific user by ID.

    Returns the user with the specified ID, or 404 if not found.
    """
    return user


@router.get(
    "/users/{user_id}/clients",
    response_model=Page[ClientResponse],
    operation_id="list_user_clients",
)
async def list_user_clients(
    user: UserModel = Depends(get_user_by_id),
    _authorized: bool = Depends(rbac["read"]),
    db: Session = Depends(get_db),
):
    query = ClientRepository(db).get_clients_by_owner_query(user.id)
    return paginate(query)


@router.post(
    "/users/{user_id}/clients",
    response_model=ClientCreateResponse,
    operation_id="create_user_client",
    status_code=201,
)
async def create_user_client(
    body: ClientCreateRequest,
    user: UserModel = Depends(get_user_by_id),
    _authorized: bool = Depends(rbac["create"]),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client, client_secret = CreateClientCommand(db).execute(
        ClientCreate(name=body.name, owner_id=user.id, created_by_id=current_user.id),
        current_user,
    )
    response = ClientResponse.model_validate(client)
    return ClientCreateResponse(**response.model_dump(), client_secret=client_secret)


@router.get("/users", response_model=Page[UserResponse], operation_id="list_users")
async def list_users(
    q: str | None = Query(
        default=None, description="Search by first_name, last_name, or email"
    ),
    _authorized: bool = Depends(rbac["read"]),
    db: Session = Depends(get_db),
):
    """
    List all users.

    Returns a paginated list of all users.
    """
    user_service = UserRepository(db)
    query = user_service.get_users_query(q=q)
    return paginate(query)
