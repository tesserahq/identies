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




