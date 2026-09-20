# Authentication and Authorization

Every request goes through the authentication middleware, then (for most routes) a Custos
permission check. This page describes exactly what happens, so you can predict the response
to any request.

## Path classes

The middleware sorts every path into one of three classes. The [API Reference](api_reference.md)
lists the class of each route in its **Access** column.

| Class | Paths | What is required |
|---|---|---|
| **Public** | `/livez`, `/readyz`, `/metrics`, `/.well-known/jwks.json`, `/oauth/token`, `/api-keys/introspect` | Nothing at the middleware. `/oauth/token` authenticates the caller with the client credentials in its body; `/api-keys/introspect` authenticates by the API key it is asked about |
| **Service only** | anything under `/internal/users`, `/oauth/token-exchange`, `/agents` | A **service-account** token: see [the service-only gate](#the-service-only-gate). No user is resolved |
| **Authenticated** | everything else | Any valid credential that resolves to an active user, then a [permission check](#permission-checks) where the route has one |

`/metrics` only exists when `OTEL_ENABLED=true`. `GET /` and `GET /openapi.json` are authenticated.

## The request pipeline

1. **Public path?** Skip authentication entirely.
2. **Find the credential.** The `X-API-Key` header if present, otherwise `Authorization: Bearer <token>`. None: `401 {"error": "Missing or invalid token"}`.
3. **Verify it.**
    - Looks like `ak_<key_id>.<secret>`: verified against the database. The key must exist, not be revoked or expired, its secret must match, and **its user must not be deleted**. Success records `last_used_at`.
    - Anything else is treated as a JWT. It is checked against the **local public key first** (tokens Identies issued itself), then against each configured JWKS provider (the OIDC provider). Allowed issuers are `OIDC_ISSUER` and `TOKEN_EXCHANGE_ISSUER`; allowed audiences are `OIDC_API_AUDIENCE` plus the `TOKEN_EXCHANGE_AUDIENCE` values.
    - Failure: `401 {"error": "Unauthorized"}`.
4. **Service-only path?** Apply [the gate](#the-service-only-gate). Pass or `403 {"error": "Forbidden"}`. Stop.
5. **Resolve the user** from the token subject:
    - An active user whose `id` or `external_id` equals the subject: use it.
    - Otherwise, if the token carries the OIDC machine-to-machine service-account claim: onboard a new service account.
    - Otherwise: fetch userinfo from the OIDC provider with the token and onboard a **human** (subject to [invite-only](#invite-only-access)).
6. **Route-level checks** (below), then the handler.

Errors from the middleware use the shape `{"error": "..."}`. Errors raised while resolving the
user or inside a route use `{"detail": ...}`.

!!! note "Deleted principals"
    A deleted user is invisible to step 5, and a deleted user's API keys and OAuth clients are
    rejected at step 3 and by `/oauth/token`. A still-valid **JWT** for a deleted user is not
    rejected explicitly: resolution falls through to fetching OIDC userinfo, which the provider
    does not accept for an Identies-issued token. Tokens minted for agents are short-lived
    (15 minutes) for this reason. See [Data Lifecycle](data_lifecycle.md).

## The service-only gate

A request to a service-only path passes only if its token is a JWT that:

1. carries the service-account claims: the `account_type` claim (default name
   `https://mylinden.family/account_type`) equal to `service_account`, **and** a non-empty client id claim
   (`https://mylinden.family/client_id`); and
2. either was **issued by Identies itself** (its issuer is `TOKEN_EXCHANGE_ISSUER`), or its client
   id is in `ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS`.

Consequences worth knowing:

- A **human** token, an **API key** and an **agent's** token all fail: none carries those claims.
- Identies only puts those claims on tokens it mints for a client owned by a **`kind = service_account`** principal. An agent's client never gets them, even though `service_account` is true for agents. This is enforced in `/oauth/token` and covered by regression tests that mint real tokens.
- For OIDC machine-to-machine tokens the allowlist is the gate: a service account is trusted only if its client id is listed.
- Every Identies-issued service-account token is trusted without an allowlist entry, which is why creating clients for service accounts is itself a privileged act (`identies.service_account` : `create`).

## Permission checks

Most authenticated routes declare a Custos permission, shown in the **Custos permission** column
as `identies.<resource>` : `<action>` (actions are `create`, `read`, `update`, `delete`). For each
request Identies asks Custos whether the authenticated user may perform that action, using the
domain `*`, and answers:

| Custos result | Response |
|---|---|
| Allowed | The handler runs |
| Denied | `403 {"detail": "Access denied"}` |
| Custos rejects the token | `401 {"detail": "Authentication failed"}` |
| Custos unreachable or erroring | `503 {"detail": "Authorization service unavailable"}` |

Custos is configured by `CUSTOS_API_URL` (a setting of the shared SDK). The SDK can cache
decisions; see [Operations](operations.md#known-issues) before enabling that.

Some routes use a different rule, visible as `-` in the permission column:

| Routes | Rule |
|---|---|
| `/me`, `/me/api-keys`, `/userinfo` | Any authenticated user, acting on themselves. `PUT /me` is refused for service accounts and agents |
| `PUT` / `DELETE /api-keys/{key_id}`, `PUT /api-keys/{key_id}/revoke` | The key must belong to the caller (`403` otherwise). No Custos check |
| `/external-accounts` (list, link, delete) | The caller's own external accounts |
| `POST /external-accounts/link-tokens` | **No check beyond authentication.** It is meant for a trusted backend; protect it at the network level |
| `/api-keys/introspect` | Deliberately **no Custos dependency**: Custos itself calls Identies to introspect keys, so a permission check here would be circular |

## Invite-only access

When `INVITE_ONLY_ACCESS=true`, a **new human** is onboarded only if their email matches an
**access rule**. Rules are managed through `/access-rules` and have a type of:

- `email`: matches that exact address, or
- `domain`: matches emails at exactly that domain (subdomains are **not** included).

Matching ignores case. A person who does not match receives `403` with

```json
{ "detail": { "title": "Access not granted", "detail": "Invitation required to access this service.",
              "code": "INVITE_REQUIRED", "email": "...", "first_name": "...", "last_name": "..." } }
```

(`email`, `first_name` and `last_name` are included when the provider supplied them) so a product
can show an "ask for an invitation" screen. Existing users and service accounts are unaffected.

## OIDC machine-to-machine tokens

A service can authenticate with a token from the OIDC provider's client-credentials flow instead
of an Identies client. Identies recognizes such a token as a service account when it carries the
`account_type` claim set to `service_account` and a `client_id` claim. With Auth0 these claims are
added by an Action on the Client Credentials exchange:

```javascript
exports.onExecuteCredentialsExchange = async (event, api) => {
  api.accessToken.setCustomClaim("https://mylinden.family/client_id", event.client.client_id);
  api.accessToken.setCustomClaim("https://mylinden.family/client_name", event.client.name);
  api.accessToken.setCustomClaim("https://mylinden.family/account_type", "service_account");
};
```

The claim names are configurable (`SERVICE_ACCOUNT_*` in [Configuration](configuration.md)). The
first time such a token is seen, a service account is created for it. To let it call the
[service-only paths](#the-service-only-gate), add its client id to
`ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS`.

## Development switch

`DISABLE_AUTH=true` removes the authentication middleware entirely. **Never enable it outside
local development.** With it on, no route has a user and permission checks cannot work.

## Configuration involved

`OIDC_DOMAIN`, `OIDC_ISSUER`, `OIDC_API_AUDIENCE`, `OIDC_ALGORITHMS`, `OIDC_JWKS_URLS`,
`OIDC_USERINFO_TIMEOUT`, `TOKEN_EXCHANGE_*`, the `SERVICE_ACCOUNT_*` claim names,
`ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS`, `INVITE_ONLY_ACCESS`, `DISABLE_AUTH`. All are described in
[Configuration](configuration.md).
