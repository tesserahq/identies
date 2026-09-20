# Credentials

How service accounts, OAuth clients, API keys and tokens work. For agents, which use the same
client credentials, see [Agents](agents.md).

## Service accounts

A service account is a principal (`kind = service_account`) for a trusted machine client. It has no
password and no interactive login.

- **Create:** `POST /service-accounts` with an email, first and last name. The account gets a generated external id (`system-<random>`) and is marked verified. Requires `identies.service_account` : `create`.
- **Auto-onboarding:** the first time an OIDC machine-to-machine token for a client is seen, a service account is created for it (its email is generated from the token's `azp`).
- **Update:** `PUT /service-accounts/{id}`. **Delete:** `DELETE /service-accounts/{id}`, a [soft delete](data_lifecycle.md) that also revokes its API keys and clients.
- Every mutation publishes the matching `user.*` event ([User Events](user_events.md)).

The service-account endpoints also list and manage **agents** today, because agents count as
non-interactive principals. Use the [agent endpoints](agents.md) for agents; moving these checks
to `kind` is tracked in [#171](https://github.com/tesserahq/identies/issues/171).

## OAuth clients and client credentials

A **client** is a credential owned by a principal: a `client_id` (`cs_...`) and a secret. Only a
hash of the secret is stored, and the secret is shown **once**, at creation or rotation.

| Field | Meaning |
|---|---|
| `owner` | The principal the client acts as. The tokens it mints have `sub` = the owner |
| `created_by` | Who created it |
| `revoked` | A revoked client cannot mint tokens |
| `expires_at` | Optional. After it, the secret stops working. Existing clients have none |
| `last_used_at` | Set on each successful token mint. Failed attempts do not count |

Create one for a service account with `POST /service-accounts/{id}/clients`, or for a user with
`POST /users/{id}/clients`. Manage it with `GET /clients/{id}`, `PUT /clients/{id}/revoke` and
`DELETE /clients/{id}`. Creation, revocation and deletion publish `client.*` events
([Events](events.md)).

### Getting a token: `POST /oauth/token`

```http
POST /oauth/token
Content-Type: application/json

{
  "grant_type": "client_credentials",
  "client_id": "cs_...",
  "client_secret": "...",
  "audience": "https://identies.tessera.com/"
}
```

```json
{ "access_token": "<RS256 JWT>", "token_type": "Bearer", "expires_in": 900 }
```

| Outcome | Response |
|---|---|
| Success | `200`; the token lasts **15 minutes** (fixed) |
| `grant_type` is not `client_credentials` | `400 Unsupported grant_type` |
| `audience` is not one of `TOKEN_EXCHANGE_AUDIENCE` | `400 Invalid audience` |
| Unknown, revoked, deleted, **expired** client, or wrong secret, or the owner is deleted | `401 Invalid client credentials` |

The request body is JSON. The token's claims are `iss` (`TOKEN_EXCHANGE_ISSUER`), `aud` (the
requested audience), `sub` (the client's owner), `iat` and `exp`. **Only** when the owner is a
`kind = service_account` principal it also carries the service-account claims
(`account_type`, `client_id`, `client_name`) that open the [service-only endpoints](authentication.md#the-service-only-gate).

Services verify these tokens locally against `GET /.well-known/jwks.json`; there is no call back to
Identies per request. The consuming service must list Identies as an auth provider with a matching
issuer and audience.

### Revocation is not instant

Revoking a client, rotating its secret or deleting its owner stops **new** tokens immediately, but
a token that was already minted stays valid until it expires — up to 15 minutes. This is the
trade-off for local verification.

## API keys

An API key is an opaque `ak_<key_id>.<secret>` string. Only a hash of the secret is stored and the
full key is shown once.

- **Create:** `POST /me/api-keys` (yourself), `POST /api-keys/users/{user_id}`, or `POST /service-accounts/{id}/api-keys`. An optional `expires_at` may be set.
- **Use:** send it as `X-API-Key: ak_...` or `Authorization: Bearer ak_...`.
- **Revoke / update / delete:** `PUT /api-keys/{id}/revoke`, `PUT /api-keys/{id}`, `DELETE /api-keys/{id}`. The key must belong to the caller. Deleting a key removes the row.
- **Validity:** not revoked, not expired, and its user not deleted.
- **Introspection:** `POST /api-keys/introspect` (public) reports `active`, `user_id`, `user`, `key_id`, `scopes` (always empty for now) and `expires_at`. Other services use it to verify keys, which costs a call to Identies on every request.

API keys remain supported for existing integrations. New features use client credentials and
short-lived JWTs instead, which is why [agents](agents.md) do not use API keys.
See [Design Decisions](decisions.md#agents-use-client-credentials-not-api-keys).

## Delegated tokens (token exchange)

A trusted service can obtain a short-lived token that acts **for a user**:
`POST /oauth/token-exchange`. See [Token Exchange](token_exchange.md).

## Choosing a credential

| You are... | Use |
|---|---|
| A person | Sign in through the OIDC provider |
| A backend service | A client on a service account, exchanged for a 15-minute JWT |
| A service that must act for a user | Token exchange |
| An AI agent | The client credentials from the [claim flow](agents.md) |
| An existing script using an API key | It keeps working; plan to move to client credentials |
