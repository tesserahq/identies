import base64
import hashlib
import json
from functools import lru_cache
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from jwt.algorithms import RSAAlgorithm

from app.config import get_settings


def _require_private_key_pem() -> str:
    settings = get_settings()
    if not settings.token_exchange_private_key_pem:
        raise ValueError("TOKEN_EXCHANGE_PRIVATE_KEY_PEM is not set")
    return settings.token_exchange_private_key_pem


def _require_public_key_pem() -> str:
    settings = get_settings()
    if not settings.token_exchange_public_key_pem:
        raise ValueError("TOKEN_EXCHANGE_PUBLIC_KEY_PEM is not set")
    return settings.token_exchange_public_key_pem


@lru_cache
def _public_key():
    public_pem = _require_public_key_pem().encode("utf-8")
    return serialization.load_pem_public_key(public_pem)


@lru_cache
def _key_id() -> str:
    settings = get_settings()
    if settings.token_exchange_key_id:
        return settings.token_exchange_key_id
    public_pem = _require_public_key_pem().encode("utf-8")
    digest = hashlib.sha256(public_pem).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")


@lru_cache
def build_jwks() -> dict[str, list[dict[str, Any]]]:
    public_key = _public_key()
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = _key_id()
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return {"keys": [jwk]}


def sign_token(claims: dict[str, Any]) -> str:
    private_key_pem = _require_private_key_pem().encode("utf-8")
    headers = {"kid": _key_id(), "typ": "JWT"}
    return jwt.encode(claims, private_key_pem, algorithm="RS256", headers=headers)
