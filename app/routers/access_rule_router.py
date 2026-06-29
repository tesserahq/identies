from fastapi import APIRouter, Depends, Request, status
from fastapi_pagination import Page, paginate as paginate_list
from fastapi_pagination.ext.sqlalchemy import paginate
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.commands.access_rules.create_access_rule_command import CreateAccessRuleCommand
from app.commands.access_rules.delete_access_rule_command import DeleteAccessRuleCommand
from app.commands.access_rules.update_access_rule_command import (
    UpdateAccessRuleCommand,
)
from app.constants.access_rule_types import AccessRuleTypes
from app.db import get_db
from app.models.access_rule import AccessRule as AccessRuleModel
from app.repositories.access_rule_repository import AccessRuleRepository
from app.routers.utils.dependencies import get_access_rule_by_id, get_current_user
from app.schemas.user import User
from app.schemas.access_rule import (
    AccessRule,
    AccessRuleCreate,
    AccessRuleTypeOption,
    AccessRuleUpdate,
)
from app.auth.rbac import build_rbac_dependencies

router = APIRouter(prefix="/access-rules", tags=["Access Rules"])


async def infer_domain(request: Request) -> Optional[str]:
    return "*"


RESOURCE = "access_rule"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.get("/", response_model=Page[AccessRule])
async def get_access_rules(
    _authorized: bool = Depends(rbac["read"]),
    db: Session = Depends(get_db),
):
    """
    Get a list of access rules with pagination.

    Returns a paginated list of access rules in the system.
    """
    access_rule_repository = AccessRuleRepository(db)
    query = access_rule_repository.get_access_rules_query()
    return paginate(query)


@router.get(
    "/types",
    response_model=Page[AccessRuleTypeOption],
    operation_id="list_access_rule_types",
)
async def list_access_rule_types(
    _authorized: bool = Depends(rbac["read"]),
):
    """
    List available access rule types for UI selection.

    Returns a paginated list of access rule type options with id and name.
    """
    return paginate_list(AccessRuleTypes.get_all_options())


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new access rule.

    Creates a new access rule with the provided data.
    The kind and value combination must be unique.
    """
    command = CreateAccessRuleCommand(db)
    access_rule = command.execute(access_rule_data, current_user)
    return access_rule


@router.put("/{access_rule_id}", response_model=AccessRule)
async def update_access_rule(
    access_rule_data: AccessRuleUpdate,
    access_rule: AccessRuleModel = Depends(get_access_rule_by_id),
    _authorized: bool = Depends(rbac["update"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing access rule.

    Updates the access rule with the specified ID using the provided data.
    Only the fields provided in the request will be updated.
    """
    command = UpdateAccessRuleCommand(db)
    updated_rule = command.execute(access_rule, access_rule_data, current_user)
    return updated_rule


@router.delete("/{access_rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_access_rule(
    access_rule_id: UUID,
    _authorized: bool = Depends(rbac["delete"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete an access rule.

    Deletes the access rule with the specified ID.
    Returns 204 No Content on successful deletion.
    """
    command = DeleteAccessRuleCommand(db)
    command.execute(access_rule_id, current_user)
