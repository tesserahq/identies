"""Router for applications."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session

from app.auth.rbac import build_rbac_dependencies
from app.db import get_db
from app.models.application import Application as ApplicationModel
from app.routers.utils.dependencies import get_application_by_id
from app.schemas.application import (
    Application,
    ApplicationBatchCreateRequest,
    ApplicationBatchCreateResponse,
    ApplicationCreate,
    ApplicationUpdate,
)
from app.repositories.application_repository import ApplicationRepository

router = APIRouter(prefix="/applications", tags=["Applications"])


async def infer_domain(_request: Request) -> Optional[str]:
    return "*"


rbac = build_rbac_dependencies(
    resource="application",
    domain_resolver=infer_domain,
)


@router.get("/", response_model=Page[Application])
async def list_applications(
    q: Optional[str] = Query(None, description="Search by name or description"),
    _authorized: bool = Depends(rbac["read"]),
    db: Session = Depends(get_db),
):
    """
    List applications with pagination.

    Returns a paginated list of applications. Optionally filter by search query.
    """
    service = ApplicationRepository(db)
    query = service.get_applications_query(q=q)
    return paginate(query)


@router.get("/{application_id}", response_model=Application)
async def get_application(
    application: ApplicationModel = Depends(get_application_by_id),
    _authorized: bool = Depends(rbac["read"]),
):
    """Get a specific application by ID."""
    return application


@router.post(
    "/batch",
    response_model=ApplicationBatchCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_applications_batch(
    body: ApplicationBatchCreateRequest,
    _authorized: bool = Depends(rbac["create"]),
    db: Session = Depends(get_db),
):
    """Create multiple applications in one request."""
    service = ApplicationRepository(db)
    applications = service.create_applications_batch(body.applications)
    return ApplicationBatchCreateResponse(items=applications)


@router.post("/", response_model=Application, status_code=status.HTTP_201_CREATED)
async def create_application(
    application_data: ApplicationCreate,
    _authorized: bool = Depends(rbac["create"]),
    db: Session = Depends(get_db),
):
    """Create a new application."""
    service = ApplicationRepository(db)
    application = service.create_application(application_data)
    return application


@router.put("/{application_id}", response_model=Application)
async def update_application(
    application: ApplicationModel = Depends(get_application_by_id),
    application_data: ApplicationUpdate = Body(...),
    _authorized: bool = Depends(rbac["update"]),
    db: Session = Depends(get_db),
):
    """Update an existing application."""
    service = ApplicationRepository(db)
    updated = service.update_application(application.id, application_data)
    if updated is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return updated


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application: ApplicationModel = Depends(get_application_by_id),
    _authorized: bool = Depends(rbac["delete"]),
    db: Session = Depends(get_db),
):
    """Delete an application."""
    service = ApplicationRepository(db)
    success = service.delete_application(application.id)
    if not success:
        raise HTTPException(status_code=404, detail="Application not found")
