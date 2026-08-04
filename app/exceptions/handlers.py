from traceback import format_exc
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.exceptions.access_rule_error import AccessRuleAlreadyExistsError
from app.exceptions.external_account_error import (
    ExternalAccountAlreadyLinkedError,
    InvalidLinkTokenError,
)
from app.exceptions.offboarding_error import (
    OffboardingAlreadyScheduledError,
    OffboardingNotScheduledError,
)
from app.exceptions.resource_not_found_error import ResourceNotFoundError
from app.exceptions.service_account_error import ServiceAccountError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AccessRuleAlreadyExistsError)
    async def access_rule_already_exists_handler(
        request: Request, exc: AccessRuleAlreadyExistsError
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ServiceAccountError)
    async def service_account_error_handler(request: Request, exc: ServiceAccountError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc)},
        )

    @app.exception_handler(InvalidLinkTokenError)
    async def invalid_link_token_handler(request: Request, exc: InvalidLinkTokenError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ExternalAccountAlreadyLinkedError)
    async def external_account_already_linked_handler(
        request: Request, exc: ExternalAccountAlreadyLinkedError
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.exception_handler(OffboardingAlreadyScheduledError)
    async def offboarding_already_scheduled_handler(
        request: Request, exc: OffboardingAlreadyScheduledError
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.exception_handler(OffboardingNotScheduledError)
    async def offboarding_not_scheduled_handler(
        request: Request, exc: OffboardingNotScheduledError
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def debug_exception_handler(request: Request, exc: Exception):

        tracback_msg = format_exc()
        return JSONResponse(
            {
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"error info: {tracback_msg}",
                # "message": f"error info: {str(exc)}",
                "data": "",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
