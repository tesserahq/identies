# Quick Setup Guide

This guide will help you get Identies up and running quickly for the first time.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11 or higher** - Check with `python --version`
- **PostgreSQL** - Version 12 or higher
- **Poetry** - Python dependency manager ([Install Poetry](https://python-poetry.org/docs/#installation))

## Step 1: Clone and Install Dependencies

```bash
# Navigate to the project directory
cd identies

# Install dependencies using Poetry
poetry install
```

## Step 2: Database Setup

Create a PostgreSQL database for Identies:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create the database
CREATE DATABASE identies;

# Exit psql
\q
```

## Step 3: Environment Configuration

Create a `.env` file in the project root with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/identies

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO

# Authentication (OIDC)
OIDC_DOMAIN=your-oidc-domain.com
OIDC_API_AUDIENCE=https://your-api-audience
OIDC_ISSUER=https://your-oidc-domain.com/
OIDC_ALGORITHMS=RS256

# Optional: Service account detection (Auth0 M2M custom claims)
SERVICE_ACCOUNT_ACCOUNT_TYPE_CLAIM=https://mylinden.family/account_type
SERVICE_ACCOUNT_ACCOUNT_TYPE_VALUE=service_account
SERVICE_ACCOUNT_CLIENT_ID_CLAIM=https://mylinden.family/client_id
SERVICE_ACCOUNT_CLIENT_NAME_CLAIM=https://mylinden.family/client_name
# Comma-separated Auth0 M2M client IDs for /internal/* and /oauth/token-exchange (Auth0 tokens only).
# Identies-issued tokens (issuer TOKEN_EXCHANGE_ISSUER) are allowed via signature + service-account claims.
ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS=conversa-client

# Custos Integration (for authorization)
CUSTOS_API_URL=http://localhost:8000

# Optional: Invite-Only Access
INVITE_ONLY_ACCESS=false

# Optional: Disable Auth (for development only)
DISABLE_AUTH=false
```

## Step 4: Run Database Migrations

```bash
# Activate the Poetry environment
poetry shell

# Run migrations
alembic upgrade head
```

## Step 5: Start the Server

```bash
# Development mode with auto-reload
poetry run dev
```

The API will be available at `http://localhost:8000` by default.

## Step 6: Verify Installation

Test that the service is running:

```bash
# Health check
curl http://localhost:8000/

# Expected response: {"message": "Hey, It is me Goku"}
```

## Next Steps

- Review the [Architecture](architecture.md) documentation to understand the system design
- Configure your OIDC provider settings
- Set up Custos integration for authorization
- Create your first user or service account via the API

## Troubleshooting

### JWKS / JWT Verification Issues

If JWT verification fails with an error similar to:

```text
jwt.exceptions.PyJWKClientConnectionError: Fail to fetch data from the url, err: "HTTP Error 403: Forbidden"
```

and accessing the JWKS endpoint manually with `curl` works:

```bash
curl https://your-domain/.well-known/jwks.json
```

then the issue is likely caused by Cloudflare blocking machine-to-machine requests.

PyJWT's `PyJWKClient` uses Python's default `urllib` client internally, which sends a `Python-urllib/<version>` user-agent. Cloudflare's Browser Integrity Check may classify this as suspicious traffic and block requests to the JWKS endpoint.

Example verification flow:

```python
import jwt

client = jwt.PyJWKClient(
    "https://your-domain/.well-known/jwks.json",
    cache_keys=True,
)

signing_key = client.get_signing_key_from_jwt(token).key
```

To resolve this issue when using Cloudflare:

1. Open the Cloudflare dashboard
2. Navigate to:
   - Security
   - WAF
   - Custom Rules
3. Create a new rule with the expression:

```text
(http.request.uri.path eq "/.well-known/jwks.json" and http.request.method eq "GET")
```

4. Set the action to:

```text
Skip
```

5. Under "More components to skip", enable only:

```text
Browser Integrity Check
```

This configuration is considered safe because the JWKS endpoint only exposes public signing keys used for JWT verification. It does not expose private keys or sensitive credentials.

Recommended JWKS endpoint behavior:

- Publicly accessible
- GET-only
- No authentication required
- Cacheable
- Exposes only public keys

Avoid disabling all WAF protections globally. Only bypass Browser Integrity Check for the JWKS endpoint.

### Database Connection Issues

- Verify PostgreSQL is running: `pg_isready`
- Check database credentials in `.env`
- Ensure the database exists: `psql -U postgres -l | grep identies`

### Migration Errors

- Ensure you're using the correct database URL
- Check that all previous migrations have been applied
- Review Alembic logs for specific errors

### Authentication Issues

- Verify OIDC configuration matches your provider
- Check that `DISABLE_AUTH=false` in production
- Ensure Vaulta is accessible if using authorization features
