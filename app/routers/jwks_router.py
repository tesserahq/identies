from fastapi import APIRouter

from app.utils.jwks import build_jwks

router = APIRouter(tags=["OAuth"])


@router.get("/.well-known/jwks.json", operation_id="get_jwks")
async def get_jwks():
    return build_jwks()
