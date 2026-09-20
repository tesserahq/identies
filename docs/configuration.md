# Configuration

Identies is configured entirely through environment variables (a `.env` file is read in
development). This page lists every setting Identies defines, plus the shared-SDK settings that
change its behaviour. A test fails if a setting is added to the code without being listed here.

## Runtime

| Variable | Default | Meaning |
|---|---|---|
| `ENV` / `ENVIRONMENT` | `development` | `test` switches the database to `TEST_DATABASE_URL`. `production` turns on Rollbar error reporting (needs `ROLLBAR_ACCESS_TOKEN`) |
| `PORT` | `8000` | Port the server listens on |
| `LOG_LEVEL` | `INFO` | Declared, but not read by Identies' own code (see [Declared but unused](#declared-but-unused)) |
| `DISABLE_AUTH` | `false` | Removes the authentication middleware. **Local development only** |
| `APP_NAME` | `identies-api` | Service name |

## Database

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/identies` | Used when `ENV` is not `test` |
| `TEST_DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/identies_test` | Used when `ENV=test` |
| `DATABASE_POOL_SIZE` | `10` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `5` | Extra connections allowed beyond the pool |
| `DB_APP_NAME` | `identies-api` | `application_name` reported to PostgreSQL |

## Identity provider (OIDC)

Used to verify human tokens and OIDC machine-to-machine tokens. See [Authentication](authentication.md).

| Variable | Default | Meaning |
|---|---|---|
| `OIDC_DOMAIN` | `test.oidc.com` | Provider domain. Also where userinfo is fetched and the default JWKS location |
| `OIDC_ISSUER` | `https://test.oidc.com/` | Expected token issuer |
| `OIDC_API_AUDIENCE` | `https://test-api` | Expected token audience |
| `OIDC_ALGORITHMS` | `RS256` | Accepted signing algorithms when verifying tokens, including Identies-issued ones |
| `OIDC_JWKS_URLS` | derived from `OIDC_DOMAIN` | Comma-separated JWKS URLs; overrides the derived one |
| `OIDC_USERINFO_TIMEOUT` | `5.0` | Seconds to wait for the provider's userinfo endpoint |

## Identies-issued tokens and token exchange

Used to sign the JWTs from `POST /oauth/token` and `POST /oauth/token-exchange`, and to verify them locally.
See [Credentials](credentials.md) and [Token Exchange](token_exchange.md).

| Variable | Default | Meaning |
|---|---|---|
| `TOKEN_EXCHANGE_PRIVATE_KEY_PEM` | none | RSA private key (PEM) used to sign. **Required to mint tokens.** Keep it secret |
| `TOKEN_EXCHANGE_PUBLIC_KEY_PEM` | none | Matching public key. Published at `/.well-known/jwks.json` and used to verify Identies-issued tokens |
| `TOKEN_EXCHANGE_KEY_ID` | derived from the public key | Stable `kid` for the published key |
| `TOKEN_EXCHANGE_ISSUER` | `https://identies.tessera.com/` | `iss` of Identies-issued tokens. A token with this issuer is treated as issued by Identies itself |
| `TOKEN_EXCHANGE_AUDIENCE` | `https://identies.tessera.com/` | Comma-separated audiences Identies will issue tokens for. `POST /oauth/token` rejects any other `audience` |
| `TOKEN_EXCHANGE_TTL_SECONDS` | `600` | Lifetime of **delegated** tokens from token exchange. Client-credential tokens are fixed at 15 minutes |
| `TOKEN_EXCHANGE_REQUIRED_SCOPE` | none | If set, the caller of `/oauth/token-exchange` must hold this scope |

## Trusting service accounts

| Variable | Default | Meaning |
|---|---|---|
| `ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS` | none | Comma-separated OIDC machine-to-machine client ids trusted on [service-only paths](authentication.md#the-service-only-gate). Identies-issued tokens do not need an entry |
| `SERVICE_ACCOUNT_ACCOUNT_TYPE_CLAIM` | `https://mylinden.family/account_type` | Claim that marks a token as a service account |
| `SERVICE_ACCOUNT_ACCOUNT_TYPE_VALUE` | `service_account` | Value that claim must have |
| `SERVICE_ACCOUNT_CLIENT_ID_CLAIM` | `https://mylinden.family/client_id` | Claim carrying the client id |
| `SERVICE_ACCOUNT_CLIENT_NAME_CLAIM` | `https://mylinden.family/client_name` | Claim carrying the client name |

## Agents

See [Agents](agents.md).

| Variable | Default | Meaning |
|---|---|---|
| `AGENT_EMAIL_DOMAIN` | `agents.example` | Domain of the synthetic agent email. It must pass email validation but never deliver. **Do not use `.invalid`, `.test` or `.localhost`: the validator rejects them** |
| `AGENT_CLAIM_TTL_MINUTES` | `15` | How long a claim code is valid |
| `AGENT_CLAIM_MAX_FAILED_ATTEMPTS` | `5` | Wrong secrets before a claim locks |
| `AGENT_CLIENT_SECRET_TTL_DAYS` | `30` | Lifetime of an agent's client secret, from claim or rotation |

## Access control

| Variable | Default | Meaning |
|---|---|---|
| `INVITE_ONLY_ACCESS` | `false` | Only onboard new humans whose email matches an [access rule](authentication.md#invite-only-access) |

## Integrations

| Variable | Default | Meaning |
|---|---|---|
| `VAULTA_API_URL` | `http://localhost:8000` | Vaulta, used to sign avatar URLs in user responses |
| `VAULTA_CLIENT_ID` | empty | Vaulta credentials for signing avatar URLs |
| `VAULTA_CLIENT_SECRET` | empty | Vaulta credentials for signing avatar URLs |

## Observability

| Variable | Default | Meaning |
|---|---|---|
| `OTEL_ENABLED` | `false` | Turn on OpenTelemetry |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4318` | OTLP endpoint |
| `OTEL_SERVICE_NAME` | `identies-api` | Service name in traces |
| `ROLLBAR_ACCESS_TOKEN` | none | Rollbar token. Only used when `ENV=production` |

## Shared SDK settings

These are defined by `tessera-sdk`, not by Identies, but they change how Identies behaves.

| Variable | Default | Meaning |
|---|---|---|
| `CUSTOS_API_URL` | `https://custos.tessera.com` | Where [permission checks](authentication.md#permission-checks) are sent |
| `AUTHORIZATION_CACHE_ENABLED` | `false` | Cache Custos decisions. **Leave off**: see [Operations](operations.md#known-issues) |
| `AUTHORIZATION_CACHE_TTL` | `300` | Seconds a cached decision lives |
| `NATS_ENABLED` | `false` | **Events are only published when this is `true`** |
| `NATS_URL` | `nats://localhost:4222` | NATS server |
| `EVENT_TYPE_PREFIX` | `com.mylinden` | Prefix of every event type ([Events](events.md)). Deployments may override it |

## Declared but unused

These exist in Identies' settings but nothing in Identies reads them. They may be read by shared
libraries; do not rely on them without checking.

| Variable | Default |
|---|---|
| `SUPER_USER_EMAIL` | none |
| `REDIS_HOST` | `localhost` |
| `REDIS_PORT` | `6379` |
| `REDIS_NAMESPACE` | `llama_index` |
| `LOG_LEVEL` | `INFO` |
