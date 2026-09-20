# Token Exchange (delegated tokens)

Token exchange lets a **trusted service** obtain a short-lived token that acts **on behalf of a
user** — for example a chat backend that calls another service as the person who is chatting.

!!! warning "This is a powerful operation"
    The caller can obtain a token for **any active user** — a human, a service account or an
    agent — with **any scope it asks for**. The only protection is that the endpoint is
    [service only](authentication.md#the-service-only-gate): a human token, an API key or an
    agent's token cannot reach it. Treat the right to call it as equivalent to impersonating every
    user, and grant it accordingly.

## `POST /oauth/token-exchange`

**Access:** service only. The caller authenticates with a service-account JWT; it must carry the
service-account claims and be trusted (issued by Identies, or an OIDC machine-to-machine client on
`ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS`).

### Request

```json
{
  "user_id": "<internal user id>",
  "requested_audience": "https://identies.tessera.com/",
  "requested_scope": "linden:read",
  "context": { "message_id": "optional", "conversation_id": "optional" }
}
```

| Field | Notes |
|---|---|
| `user_id` | UUID of an **active** user (deleted users are not found) |
| `requested_audience` | Must be one of `TOKEN_EXCHANGE_AUDIENCE` |
| `requested_scope` | A space-delimited string or a list. Copied into the token as requested |
| `context` | Accepted but not currently used |

### Response

```json
{ "access_token": "<RS256 JWT>", "token_type": "Bearer", "expires_in": 600, "scope": "linden:read" }
```

### Errors

| Situation | Response |
|---|---|
| Not a trusted service-account token | `403 {"error": "Forbidden"}` (from the middleware) |
| `TOKEN_EXCHANGE_REQUIRED_SCOPE` is set and the caller's token lacks it | `403 Insufficient scope` |
| The caller's client id cannot be determined | `403 Actor identity not found` |
| `requested_audience` not allowed | `400 Invalid audience` |
| Unknown or deleted user | `404 User not found` |

## Token claims

| Claim | Value |
|---|---|
| `iss` | `TOKEN_EXCHANGE_ISSUER` |
| `aud` | The requested audience |
| `sub` | The **user** the token acts for |
| `act` | The calling service (its client id) |
| `scope` | The requested scope |
| `iat`, `exp` | Issued at, and expiry after `TOKEN_EXCHANGE_TTL_SECONDS` (default **600**) |
| `jti` | A unique token id |

Delegated tokens carry **no service-account claims**, so they cannot be used to call the
service-only endpoints, only to act as the user elsewhere.

## Verifying these tokens

Downstream services verify the signature locally against `GET /.well-known/jwks.json` (public, no
authentication, one RS256 key), checking the issuer and audience. The consuming service must list
Identies as an auth provider ([Operations](operations.md#a-service-that-must-accept-identies-issued-tokens-agents-service-accounts)).

## Difference from client credentials

| | Client credentials (`/oauth/token`) | Token exchange |
|---|---|---|
| Acts as | The client's **owner** | Any **user** the caller names |
| Caller proves | Its own client id and secret | A service-account token |
| Lifetime | 15 minutes (fixed) | `TOKEN_EXCHANGE_TTL_SECONDS` |
| Used for | A service or agent acting as itself | A service acting for a person |

See [Credentials](credentials.md).

## Configuration

`TOKEN_EXCHANGE_PRIVATE_KEY_PEM`, `TOKEN_EXCHANGE_PUBLIC_KEY_PEM`, `TOKEN_EXCHANGE_KEY_ID`,
`TOKEN_EXCHANGE_ISSUER`, `TOKEN_EXCHANGE_AUDIENCE`, `TOKEN_EXCHANGE_TTL_SECONDS`,
`TOKEN_EXCHANGE_REQUIRED_SCOPE`, `ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS` and the `SERVICE_ACCOUNT_*`
claim names are all described in [Configuration](configuration.md).
