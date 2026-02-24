from fastapi import APIRouter, Depends, Request, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from typing import Optional

from app.auth.rbac import build_rbac_dependencies
from app.db import get_db
from app.models.user import User as UserModel
from app.routers.utils.dependencies import get_user_by_id
from app.schemas.user import UserResponse
from app.services.user_service import UserService
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
    user_service = UserService(db)
    query = user_service.get_users_query(q=q)
    return paginate(query)
