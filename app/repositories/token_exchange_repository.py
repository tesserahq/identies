from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.config import Settings
from app.utils.jwks import sign_token


@dataclass(frozen=True)
class TokenExchangeResult:
    access_token: str
    expires_in: int
    scope: str


class TokenExchangeRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def mint_delegated_token(
        self,
        user_id: UUID,
        actor: str,
        audience: str,
        scope: str,
    ) -> TokenExchangeResult:
        now = datetime.now(timezone.utc)
        expires_in = int(self.settings.token_exchange_ttl_seconds)
        expires_at = now + timedelta(seconds=expires_in)

        claims = {
            "iss": self.settings.token_exchange_issuer,
            "aud": audience,
            "sub": str(user_id),
            "act": actor,
            "scope": scope,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": str(uuid4()),
        }

        token = sign_token(claims)

        return TokenExchangeResult(
            access_token=token,
            expires_in=expires_in,
            scope=scope,
        )
