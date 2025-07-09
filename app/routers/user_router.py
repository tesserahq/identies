from fastapi import APIRouter, Depends, Request
from app.utils.auth import get_current_user
from app.schemas.user import User
from app.db import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/userinfo", tags=["User"])


@router.get("/", response_model=User)
async def get_current_user_info(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get information about the currently authenticated user.

    Returns the user profile information for the authenticated user making the request.
    """
    user = await get_current_user(request)

    return user
