# Token Exchange (OBO) in Identies

Identies exposes a token exchange endpoint for trusted service accounts to mint
short-lived delegated access tokens on behalf of a user.

## Endpoints

### POST `/oauth/token-exchange`

Exchanges a service account token for a delegated access token.

Request body:

```json
{
  "user_id": "USER_ID",
  "requested_audience": "linden",
  "requested_scope": "linden:read",
  "context": {
    "message_id": "optional",
    "conversation_id": "optional"
  }
}
```

Response:

```json
{
  "access_token": "JWT_TOKEN",
  "token_type": "Bearer",
  "expires_in": 600,
  "scope": "linden:read"
}
```

### GET `/.well-known/jwks.json`

Public JWKS endpoint used by downstream services to validate tokens signed by
Identies.

## Token claims

Delegated tokens include:

- `iss`: from `TOKEN_EXCHANGE_ISSUER`
- `aud`: requested audience (must be allowed)
- `sub`: internal user id
- `act`: actor service identity (client id)
- `scope`: requested scope (space-delimited string)
- `iat`, `exp`: issued-at and expiration timestamps
- `jti`: unique token id

## Configuration

These env vars control token exchange behavior:

- `TOKEN_EXCHANGE_PRIVATE_KEY_PEM`: RSA private key (PEM)
- `TOKEN_EXCHANGE_PUBLIC_KEY_PEM`: RSA public key (PEM)
- `TOKEN_EXCHANGE_KEY_ID`: optional stable key id (kid)
- `TOKEN_EXCHANGE_ISSUER`: token issuer (default `identies`)
- `TOKEN_EXCHANGE_AUDIENCE`: allowed audience(s), comma-separated
- `TOKEN_EXCHANGE_TTL_SECONDS`: token TTL in seconds (default 600)
- `TOKEN_EXCHANGE_REQUIRED_SCOPE`: required scope on the M2M token (default `token:exchange`)
- `ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS`: comma-separated allowlist for M2M clients

Service account claims use existing settings:

- `SERVICE_ACCOUNT_ACCOUNT_TYPE_CLAIM`
- `SERVICE_ACCOUNT_ACCOUNT_TYPE_VALUE`
- `SERVICE_ACCOUNT_CLIENT_ID_CLAIM`
