import logging
from app.middleware.db_session import DBSessionMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
import rollbar
from rollbar.logger import RollbarHandler

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.telemetry import setup_tracing
from app.exceptions.handlers import register_exception_handlers
from app.core.logging_config import get_logger
from app.db import db_manager
from fastapi_pagination import add_pagination
from app.utils.metrics import PrometheusMiddleware, metrics


class EndpointFilter(logging.Filter):
    # Uvicorn endpoint access log filter
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("GET /metrics") == -1


# Filter out /endpoint
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())


def create_app(testing: bool = False, auth_middleware=None) -> FastAPI:
    logger = get_logger()
    settings = get_settings()

    if settings.is_production:
        # Initialize Rollbar SDK with your server-side access token
        rollbar.init(
            settings.rollbar_access_token,
            environment=settings.environment,
            handler="async",
        )

        # Report ERROR and above to Rollbar
        rollbar_handler = RollbarHandler()
        rollbar_handler.setLevel(logging.ERROR)

        # Attach Rollbar handler to the root logger
        logger.addHandler(rollbar_handler)

    app = FastAPI()

    if not testing and not settings.disable_auth:
        logger.info("Main: Adding authentication middleware")
        from app.middleware.authentication_middleware import AuthenticationMiddleware

        app.add_middleware(AuthenticationMiddleware, database_manager=db_manager)

        # Setting metrics middleware
        app.add_middleware(PrometheusMiddleware, app_name=settings.app_name)
        app.add_route("/metrics", metrics)
    else:
        logger.info("Main: No authentication middleware")
        if auth_middleware:
            app.add_middleware(auth_middleware)

    # TODO: Restrict this to the allowed origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Puedes restringir esto a dominios específicos
        allow_credentials=True,
        allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
        allow_headers=["*"],  # Permitir todos los headers
    )

    register_exception_handlers(app)

    # Include routers
    from app.routers.user_router import router as user_router
    from app.routers.userinfo_router import router as userinfo_router
    from app.routers.api_keys import router as api_keys_router
    from app.routers.access_rule_router import router as access_rule_router
    from app.routers.service_account_router import router as service_account_router
    from app.routers.me_router import router as me_router
    from app.routers.system_router import router as system_router

    app.include_router(user_router)
    app.include_router(userinfo_router)
    app.include_router(api_keys_router)
    app.include_router(access_rule_router)
    app.include_router(service_account_router)
    app.include_router(me_router)
    app.include_router(system_router)

    # Initialize fastapi-pagination
    add_pagination(app)

    return app


# Production app instance
app = create_app()

settings = get_settings()
if settings.otel_enabled:
    tracer_provider = setup_tracing()  # Or use env/config
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)


@app.get("/")
def main_route():
    return {"message": "Hey, It is me Goku"}
