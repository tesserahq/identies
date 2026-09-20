# API Reference

Interactive documentation (`/docs`, `/redoc`) is switched off. The route table below is the
complete list of API routes. An OpenAPI document is available at `GET /openapi.json`, but only
to an authenticated caller.

Three routes are defined outside the application factory, on the production app instance, and are
therefore **not** in the generated table:

| Route | Access | Notes |
|---|---|---|
| `GET /` | Authenticated | Returns `{"message": "Hey, It is me Goku"}`. Not a health check; use `/livez` |
| `GET /openapi.json` | Authenticated | The OpenAPI document |
| `GET /metrics` | Public | Prometheus metrics; only present when `OTEL_ENABLED=true` |

## How to read the table

- **Access** is the [path class](authentication.md#path-classes): **Public** (no credentials at
  the middleware), **Service only** (a trusted service-account token, no user), or
  **Authenticated** (any credential that resolves to an active user).
- **Custos permission** is the `identies.<resource>` : `<action>` checked for the user. `-` means
  the route has no Custos check; some of those still have a rule of their own
  ([Permission checks](authentication.md#permission-checks)).
- **Operation** is the stable `operationId`.

The table below is **generated from the code** and verified by a test. To update it after
changing a route:

```bash
poetry run python -m tests.docs.route_inventory --write
```

<!-- BEGIN GENERATED ROUTES (tests/docs/route_inventory.py) -->

| Method | Path | Access | Custos permission | Operation |
|---|---|---|---|---|
| GET | `/.well-known/jwks.json` | Public | - | `get_jwks` |
| GET | `/access-rules/` | Authenticated | `identies.access_rule` : `read` | `get_access_rules` |
| POST | `/access-rules/` | Authenticated | `identies.access_rule` : `create` | `create_access_rule` |
| GET | `/access-rules/types` | Authenticated | `identies.access_rule` : `read` | `list_access_rule_types` |
| DELETE | `/access-rules/{access_rule_id}` | Authenticated | `identies.access_rule` : `delete` | `delete_access_rule` |
| GET | `/access-rules/{access_rule_id}` | Authenticated | `identies.access_rule` : `read` | `get_access_rule` |
| PUT | `/access-rules/{access_rule_id}` | Authenticated | `identies.access_rule` : `update` | `update_access_rule` |
| POST | `/agents` | Service only | - | `create_agent` |
| POST | `/agents/claim` | Service only | - | `claim_agent` |
| DELETE | `/agents/{agent_id}` | Service only | - | `delete_agent` |
| GET | `/agents/{agent_id}` | Service only | - | `get_agent` |
| POST | `/agents/{agent_id}/claim-codes` | Service only | - | `issue_agent_claim_code` |
| POST | `/agents/{agent_id}/revoke` | Service only | - | `revoke_agent` |
| POST | `/agents/{agent_id}/rotate` | Service only | - | `rotate_agent_credentials` |
| POST | `/api-keys/introspect` | Public | - | `introspect_api_key` |
| GET | `/api-keys/users/{user_id}` | Authenticated | `identies.api_key` : `read` | `list_user_api_keys` |
| POST | `/api-keys/users/{user_id}` | Authenticated | `identies.api_key` : `create` | `create_user_api_key` |
| DELETE | `/api-keys/users/{user_id}/{key_id}` | Authenticated | `identies.api_key` : `delete` | `delete_user_api_key` |
| DELETE | `/api-keys/{key_id}` | Authenticated | - | `delete_api_key` |
| GET | `/api-keys/{key_id}` | Authenticated | `identies.api_key` : `read` | `get_api_key` |
| PUT | `/api-keys/{key_id}` | Authenticated | - | `update_api_key` |
| PUT | `/api-keys/{key_id}/revoke` | Authenticated | - | `revoke_api_key` |
| GET | `/applications/` | Authenticated | `identies.application` : `read` | `list_applications` |
| POST | `/applications/` | Authenticated | `identies.application` : `create` | `create_application` |
| POST | `/applications/batch` | Authenticated | `identies.application` : `create` | `create_applications_batch` |
| DELETE | `/applications/{application_id}` | Authenticated | `identies.application` : `delete` | `delete_application` |
| GET | `/applications/{application_id}` | Authenticated | `identies.application` : `read` | `get_application` |
| PUT | `/applications/{application_id}` | Authenticated | `identies.application` : `update` | `update_application` |
| DELETE | `/clients/{client_id}` | Authenticated | `identies.client` : `delete` | `delete_client` |
| GET | `/clients/{client_id}` | Authenticated | `identies.client` : `read` | `get_client` |
| PUT | `/clients/{client_id}/revoke` | Authenticated | `identies.client` : `update` | `revoke_client` |
| GET | `/external-accounts` | Authenticated | - | `list_external_accounts` |
| POST | `/external-accounts/check` | Authenticated | `identies.external_account` : `read` | `check_external_account` |
| POST | `/external-accounts/link` | Authenticated | - | `link_external_account` |
| POST | `/external-accounts/link-tokens` | Authenticated | - | `create_link_token` |
| DELETE | `/external-accounts/{external_account_id}` | Authenticated | - | `delete_external_account` |
| GET | `/internal/users/{user_id}` | Service only | - | `get_user_by_id` |
| GET | `/livez` | Public | - | `livez` |
| GET | `/me` | Authenticated | - | `get_me` |
| PUT | `/me` | Authenticated | - | `update_me` |
| GET | `/me/api-keys` | Authenticated | - | `list_user_api_keys` |
| POST | `/me/api-keys` | Authenticated | - | `create_me_api_key` |
| POST | `/oauth/token` | Public | - | `oauth_token` |
| POST | `/oauth/token-exchange` | Service only | - | `token_exchange` |
| GET | `/readyz` | Public | - | `readyz` |
| GET | `/service-accounts` | Authenticated | `identies.service_account` : `read` | `list_service_accounts` |
| POST | `/service-accounts` | Authenticated | `identies.service_account` : `create` | `create_service_account` |
| DELETE | `/service-accounts/{service_account_id}` | Authenticated | `identies.service_account` : `delete` | `delete_service_account` |
| GET | `/service-accounts/{service_account_id}` | Authenticated | `identies.service_account` : `read` | `get_service_account` |
| PUT | `/service-accounts/{service_account_id}` | Authenticated | `identies.service_account` : `update` | `update_service_account` |
| GET | `/service-accounts/{service_account_id}/api-keys` | Authenticated | `identies.service_account` : `read` | `list_service_account_api_keys` |
| POST | `/service-accounts/{service_account_id}/api-keys` | Authenticated | `identies.service_account` : `create` | `create_service_account_api_key` |
| GET | `/service-accounts/{service_account_id}/clients` | Authenticated | `identies.service_account` : `read` | `list_service_account_clients` |
| POST | `/service-accounts/{service_account_id}/clients` | Authenticated | `identies.service_account` : `create` | `create_service_account_client` |
| GET | `/userinfo` | Authenticated | - | `get_userinfo` |
| GET | `/users` | Authenticated | `identies.user` : `read` | `list_users` |
| GET | `/users/{user_id}` | Authenticated | `identies.user` : `read` | `get_user_by_id` |
| GET | `/users/{user_id}/clients` | Authenticated | `identies.user` : `read` | `list_user_clients` |
| POST | `/users/{user_id}/clients` | Authenticated | `identies.user` : `create` | `create_user_client` |
| GET | `/users/{user_id}/external-accounts` | Authenticated | `identies.external_account` : `read`, `identies.user` : `read` | `list_user_external_accounts` |

<!-- END GENERATED ROUTES -->

## Conventions

- **Lists** return a page: `{"items": [...], "total": n, "page": 1, "size": 50, "pages": n}`. Use the `page` and `size` query parameters.
- **Errors from routes** are `{"detail": ...}`. **Errors from the middleware** are `{"error": ...}`. Common statuses: `400` bad input or invalid code, `401` missing or invalid credentials, `403` not allowed, `404` not found (including "exists but is not the right kind"), `409` conflict, `422` request validation, `503` Custos unavailable.
- **Secrets are shown once**: client secrets, API key secrets and claim codes appear only in the response that creates them.
- **Deleted principals are `404`**, not `410`.

## Notes by area

### Users, `/me`, `/userinfo`

`GET /users` lists **humans only** (service accounts and agents are excluded); `GET /users/{id}` and
`GET /internal/users/{id}` return any active user. `PUT /me` updates the caller's own profile
and is refused (`403`) for service accounts and agents. Every user response includes `kind`.
`GET /internal/users/{id}` is [service only](authentication.md#the-service-only-gate).

### Service accounts

Manage the service accounts and, under each, their API keys and OAuth clients. These routes also
list and manage agents today ([#171](https://github.com/tesserahq/identies/issues/171)); use `/agents`
for agents. See [Credentials](credentials.md#service-accounts).

### Agents

All `/agents` routes are service only and act only on **active agents**: an id that belongs to a
human, a service account, a deleted user or nothing at all is a `404`. See [Agents](agents.md).

### Clients, `/oauth/token` and token exchange

`POST /oauth/token` is public and authenticates with the client credentials in its JSON body.
`POST /oauth/token-exchange` is service only. `GET /.well-known/jwks.json` publishes the public
signing key. See [Credentials](credentials.md) and [Token Exchange](token_exchange.md).

### API keys

`/me/api-keys` acts on the caller. `PUT` and `DELETE` on `/api-keys/{key_id}` (and `/revoke`) require
that the key belongs to the caller. `POST /api-keys/introspect` is public on purpose (Custos calls
it, so it cannot itself depend on Custos). See [Credentials](credentials.md#api-keys).

### Access rules

Invite-only rules of type `email` or `domain`. `GET /access-rules/types` lists the types. See
[Authentication](authentication.md#invite-only-access).

### External accounts

Link a person to accounts on outside platforms. A trusted backend calls `POST
/external-accounts/link-tokens` to create a short-lived, single-use token, and the person then
calls `POST /external-accounts/link` with it; `POST /external-accounts/check` answers whether a
platform account is linked. `link-tokens` has no permission check beyond authentication, so
restrict who can reach it.

### Applications

A small registry of applications (name, url, logo, description). `POST /applications/batch` creates
several at once.

### Health

`GET /livez` and `GET /readyz` are public probes. Identies registers no readiness probes, so `/readyz` does not verify the database.
