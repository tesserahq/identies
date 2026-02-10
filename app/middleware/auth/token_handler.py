import jwt
from fastapi import HTTPException, status
from app.config import get_settings
from app.middleware.auth.exceptions import UnauthorizedException


class TokenHandler:
    """Does all the token verification using PyJWT"""

    def __init__(self):
        self.config = get_settings()

        jwks_urls = self.config.get_oidc_jwks_urls()
        self.jwks_clients = [
            jwt.PyJWKClient(jwks_url, cache_keys=True) for jwks_url in jwks_urls
        ]
        self.local_public_key_pem = self.config.token_exchange_public_key_pem

        if not self.jwks_clients and not self.local_public_key_pem:
            raise ValueError("OIDC JWKS URLs or local public key must be configured.")

    def _allowed_issuers(self) -> list[str]:
        issuers = [self.config.oidc_issuer, self.config.token_exchange_issuer]
        return [issuer for issuer in dict.fromkeys(issuers) if issuer]

    def _allowed_audiences(self) -> list[str]:
        audiences = [self.config.oidc_api_audience]
        audiences.extend(self.config.get_token_exchange_audiences())
        return [audience for audience in dict.fromkeys(audiences) if audience]

    def verify(self, token: str):
        # This gets the 'kid' from the passed token
        allowed_issuers = self._allowed_issuers()
        allowed_audiences = self._allowed_audiences()
        last_error: Exception | None = None

        if self.local_public_key_pem:
            try:
                payload = jwt.decode(
                    token,
                    self.local_public_key_pem,
                    algorithms=self.config.oidc_algorithms,
                    audience=allowed_audiences,
                    issuer=allowed_issuers,
                )
                return payload
            except Exception as error:
                last_error = error

        for jwks_client in self.jwks_clients:
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(token).key
            except jwt.exceptions.PyJWKClientError as error:
                last_error = error
                continue
            except jwt.exceptions.DecodeError as error:
                last_error = error
                continue

            try:
                payload = jwt.decode(
                    token,
                    signing_key,
                    algorithms=self.config.oidc_algorithms,
                    audience=allowed_audiences,
                    issuer=allowed_issuers,
                )
                return payload
            except Exception as error:
                last_error = error
                continue

        if last_error:
            raise UnauthorizedException(str(last_error))
        raise UnauthorizedException("Unable to verify token")
