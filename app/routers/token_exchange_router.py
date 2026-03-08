from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.schemas.token_exchange import TokenExchangeRequest, TokenExchangeResponse
from app.services.token_exchange_service import TokenExchangeService
from app.services.user_service import UserService
from app.core.logging_config import get_logger

logger = get_logger()

router = APIRouter(prefix="/oauth", tags=["OAuth"])


def _normalize_scope(scope_value: str | list[str]) -> str:
    if isinstance(scope_value, list):
        return " ".join(s.strip() for s in scope_value if s.strip())
    return " ".join(s.strip() for s in scope_value.split() if s.strip())


def _scope_includes(payload_scope: str | list[str] | None, required: str) -> bool:
    if not payload_scope or not required:
        return False
    if isinstance(payload_scope, list):
        scope_values = payload_scope
    else:
        scope_values = payload_scope.split()
    return required in scope_values


def _extract_actor(payload: dict, claim_name: str) -> str | None:
    actor = payload.get(claim_name)
    if isinstance(actor, str) and actor:
        return actor
    actor = payload.get("azp")
    if isinstance(actor, str) and actor:
        return actor
    return None


@router.post(
    "/token-exchange",
    response_model=TokenExchangeResponse,
    operation_id="token_exchange",
)
async def token_exchange(
    body: TokenExchangeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    settings = get_settings()

    payload = getattr(request.state, "jwt_payload", None)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token",
        )

    if settings.token_exchange_required_scope and not _scope_includes(
        payload.get("scope"), settings.token_exchange_required_scope
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient scope",
        )

    actor = _extract_actor(payload, settings.service_account_client_id_claim)
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Actor identity not found",
        )

    allowed_audiences = settings.get_token_exchange_audiences()
    if body.requested_audience not in allowed_audiences:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audience",
        )

    user = UserService(db).get_user(body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    scope = _normalize_scope(body.requested_scope)
    service = TokenExchangeService(settings)
    result = service.mint_delegated_token(
        user_id=user.id,
        actor=actor,
        audience=body.requested_audience,
        scope=scope,
    )


    logger.info(f"Token exchange result: {result.access_token}")

    return TokenExchangeResponse(
        access_token=result.access_token,
        expires_in=result.expires_in,
        scope=result.scope,
    )
