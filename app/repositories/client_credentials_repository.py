from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.utils.jwks import sign_token


@dataclass(frozen=True)
class ClientTokenResult:
    access_token: str
    expires_in: int


@dataclass(frozen=True)
class ServiceAccountClientContext:
    client_id: str
    client_name: str


class ClientCredentialsRepository:
    TTL_SECONDS = 900  # 15 minutes

    def __init__(self, settings: Settings):
        self.settings = settings

    def mint_token(
        self,
        owner_id: str,
        audience: str,
        *,
        service_account_client: ServiceAccountClientContext | None = None,
    ) -> ClientTokenResult:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.TTL_SECONDS)

        claims = {
            "iss": self.settings.token_exchange_issuer,
            "aud": audience,
            "sub": owner_id,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }

        if service_account_client is not None:
            claims[self.settings.service_account_client_id_claim] = (
                service_account_client.client_id
            )
            claims[self.settings.service_account_client_name_claim] = (
                service_account_client.client_name
            )
            claims[self.settings.service_account_account_type_claim] = (
                self.settings.service_account_account_type_value
            )

        token = sign_token(claims)
        return ClientTokenResult(access_token=token, expires_in=self.TTL_SECONDS)
