from fastapi import APIRouter, Depends, Query, Request, status
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.commands.access_rules.create_access_rule_command import CreateAccessRuleCommand
from app.commands.access_rules.delete_access_rule_command import DeleteAccessRuleCommand
from app.commands.access_rules.update_access_rule_command import (
    UpdateAccessRuleCommand,
)
from app.db import get_db
from app.models.access_rule import AccessRule as AccessRuleModel
from app.repositories.access_rule_repository import AccessRuleRepository
from app.routers.utils.dependencies import get_access_rule_by_id
from app.schemas.access_rule import AccessRule, AccessRuleCreate, AccessRuleUpdate
from app.auth.rbac import build_rbac_dependencies

router = APIRouter(prefix="/access-rules", tags=["Access Rules"])


async def infer_domain(request: Request) -> Optional[str]:
    return "*"


RESOURCE = "access_rule"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.get("/", response_model=dict)
async def get_access_rules(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    _authorized: bool = Depends(rbac["read"]),
    db: Session = Depends(get_db),
):
    """
    Get a list of access rules with pagination.

    Returns a paginated list of access rules in the system.
    """
    access_rule_repository = AccessRuleRepository(db)
    access_rules = access_rule_repository.get_access_rules(skip=skip, limit=limit)

    # Convert SQLAlchemy models to Pydantic schemas
    access_rule_schemas = [AccessRule.model_validate(rule) for rule in access_rules]

    return {"data": access_rule_schemas}


@router.get("/search/", response_model=dict)
async def search_access_rules(
    kind: Optional[str] = Query(None, description="Filter by access rule kind"),
    value: Optional[str] = Query(None, description="Filter by access rule value"),
    note: Optional[str] = Query(None, description="Filter by note content"),
    _authorized: bool = Depends(rbac["read"]),
    db: Session = Depends(get_db),
):
    """
    Search access rules with dynamic filters.

    Allows searching access rules using various filter criteria.
    All filters are optional and can be combined.
    """
    access_rule_repository = AccessRuleRepository(db)
    filters: dict = {}
    if kind is not None:
        filters["kind"] = kind
    if value is not None:
        filters["value"] = value
    if note is not None:
        filters["note"] = {"operator": "ilike", "value": f"%{note}%"}

    access_rules = access_rule_repository.search(filters)

    # Convert SQLAlchemy models to Pydantic schemas
    access_rule_schemas = [AccessRule.model_validate(rule) for rule in access_rules]

    return {"data": access_rule_schemas}


@router.get("/{access_rule_id}", response_model=AccessRule)
async def get_access_rule(
    access_rule: AccessRuleModel = Depends(get_access_rule_by_id),
    _authorized: bool = Depends(rbac["read"]),
):
    """
    Get a specific access rule by ID.

    Returns the access rule with the specified ID, or 404 if not found.
    """
    return access_rule


@router.post("/", response_model=AccessRule)
async def create_access_rule(
    access_rule_data: AccessRuleCreate,
    _authorized: bool = Depends(rbac["create"]),
    db: Session = Depends(get_db),
):
    """
    Create a new access rule.

    Creates a new access rule with the provided data.
    The kind and value combination must be unique.
    """
    command = CreateAccessRuleCommand(db)
    access_rule = command.execute(access_rule_data)
    return access_rule


@router.put("/{access_rule_id}", response_model=AccessRule)
async def update_access_rule(
    access_rule_data: AccessRuleUpdate,
    access_rule: AccessRuleModel = Depends(get_access_rule_by_id),
    _authorized: bool = Depends(rbac["update"]),
    db: Session = Depends(get_db),
):
    """
    Update an existing access rule.

    Updates the access rule with the specified ID using the provided data.
    Only the fields provided in the request will be updated.
    """
    command = UpdateAccessRuleCommand(db)
    updated_rule = command.execute(access_rule, access_rule_data)
    return updated_rule


@router.delete("/{access_rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_access_rule(
    access_rule_id: UUID,
    _authorized: bool = Depends(rbac["delete"]),
    db: Session = Depends(get_db),
):
    """
    Delete an access rule.

    Deletes the access rule with the specified ID.
    Returns 204 No Content on successful deletion.
    """
    command = DeleteAccessRuleCommand(db)
    command.execute(access_rule_id)
