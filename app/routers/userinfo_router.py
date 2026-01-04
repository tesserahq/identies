from fastapi import APIRouter, Depends, Request
from typing import Optional
from app.utils.auth import get_current_user
from app.schemas.user import UserResponse
from app.auth.rbac import build_rbac_dependencies

router = APIRouter(tags=["UserInfo"])


async def infer_domain(request: Request) -> Optional[str]:
    return "*"


RESOURCE = "userinfo"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.get("/userinfo", response_model=UserResponse, operation_id="get_userinfo")
async def get_current_user_info(
    _authorized: bool = Depends(rbac["read"]),
    current_user=Depends(get_current_user),
):
    """
    Get information about the currently authenticated user.

    Returns the user profile information for the authenticated user making the request.
    """
    return current_user
