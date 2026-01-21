import os
from pydantic import AliasChoices, Field, model_validator
from typing import Optional
from pydantic_settings import BaseSettings
from sqlalchemy.engine.url import make_url, URL

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/identies"
DEFAULT_TEST_DATABASE_URL = (
    "postgresql://postgres:postgres@localhost:5432/identies_test"
)

SERVICE_NAME = "identies-api"


class Settings(BaseSettings):
    app_name: str = SERVICE_NAME
    otel_enabled: bool = Field(default=False, json_schema_extra={"env": "OTEL_ENABLED"})
    database_url: Optional[str] = None  # Will be set dynamically
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENV", "ENVIRONMENT"),
    )
    log_level: str = Field(default="INFO", json_schema_extra={"env": "LOG_LEVEL"})
    disable_auth: bool = Field(default=False, json_schema_extra={"env": "DISABLE_AUTH"})
    rollbar_access_token: Optional[str] = Field(
        default=None, json_schema_extra={"env": "ROLLBAR_ACCESS_TOKEN"}
    )  # Optional field
    super_user_email: Optional[str] = Field(
        default=None, json_schema_extra={"env": "SUPER_USER_EMAIL"}
    )  # Optional field for super user setup
    vaulta_api_url: str = Field(
        default="http://localhost:8000", json_schema_extra={"env": "VAULTA_API_URL"}
    )
    vaulta_client_id: str = Field(
        default="", json_schema_extra={"env": "VAULTA_CLIENT_ID"}
    )
    vaulta_client_secret: str = Field(
        default="", json_schema_extra={"env": "VAULTA_CLIENT_SECRET"}
    )

    oidc_domain: str = "test.oidc.com"
    oidc_api_audience: str = "https://test-api"
    oidc_issuer: str = "https://test.oidc.com/"
    oidc_algorithms: str = "RS256"

    # Service account detection (Auth0 M2M custom claims)
    service_account_account_type_claim: str = Field(
        default="https://mylinden.family/account_type",
        json_schema_extra={"env": "SERVICE_ACCOUNT_ACCOUNT_TYPE_CLAIM"},
    )
    service_account_account_type_value: str = Field(
        default="service_account",
        json_schema_extra={"env": "SERVICE_ACCOUNT_ACCOUNT_TYPE_VALUE"},
    )
    service_account_client_id_claim: str = Field(
        default="https://mylinden.family/client_id",
        json_schema_extra={"env": "SERVICE_ACCOUNT_CLIENT_ID_CLAIM"},
    )

    allowed_service_account_client_ids: Optional[str] = Field(
        default=None, json_schema_extra={"env": "ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS"}
    )

    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = SERVICE_NAME.lower()
    redis_host: str = Field(
        default="localhost", json_schema_extra={"env": "REDIS_HOST"}
    )
    redis_port: int = Field(default=6379, json_schema_extra={"env": "REDIS_PORT"})
    redis_namespace: str = Field(
        default="llama_index", json_schema_extra={"env": "REDIS_NAMESPACE"}
    )
    invite_only_access: bool = Field(
        default=False, json_schema_extra={"env": "INVITE_ONLY_ACCESS"}
    )
    port: int = Field(default=8000, json_schema_extra={"env": "PORT"})
    database_pool_size: int = Field(
        default=10, json_schema_extra={"env": "DATABASE_POOL_SIZE"}
    )
    database_max_overflow: int = Field(
        default=5, json_schema_extra={"env": "DATABASE_MAX_OVERFLOW"}
    )
    db_app_name: str = Field(
        default="identies-api", json_schema_extra={"env": "DB_APP_NAME"}
    )

    def get_allowed_service_account_client_ids(self) -> list[str]:
        """
        Parse allowed_service_account_client_ids as a comma-separated string from env.
        """
        env_val = self.allowed_service_account_client_ids
        if env_val:
            return [v.strip() for v in env_val.split(",") if v.strip()]
        return []

    @model_validator(mode="before")
    def set_database_url(cls, values):
        """Set the database_url dynamically based on the environment field."""
        environment = values.get("environment", os.getenv("ENV", "development"))
        if environment.lower() == "test":
            values["database_url"] = os.getenv(
                "TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL
            )
        else:
            values["database_url"] = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

        return values

    @property
    def is_production(self) -> bool:
        """Check if the current environment is production."""
        return self.environment.lower() == "production"

    @property
    def is_test(self) -> bool:
        """Check if the current environment is test."""
        return self.environment.lower() == "test"

    @property
    def database_url_obj(self) -> URL:
        """Return the database URL as a URL object using sqlalchemy's make_url."""
        if not self.database_url:
            raise ValueError("Database URL is not set.")
        return make_url(self.database_url)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra environment variables


def get_settings() -> Settings:
    """Get application settings with required environment variables."""
    return Settings()
