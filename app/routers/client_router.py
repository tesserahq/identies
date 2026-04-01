from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.rbac import build_rbac_dependencies
from app.commands.clients.delete_client_command import DeleteClientCommand
from app.commands.clients.revoke_client_command import RevokeClientCommand
from app.db import get_db
from app.models.client import Client
from app.models.user import User
from app.routers.utils.dependencies import get_client_by_id, get_current_user
from app.schemas.client import ClientResponse

router = APIRouter(prefix="/clients", tags=["Clients"])


async def infer_domain(_request: Request) -> Optional[str]:
    return "*"


RESOURCE = "client"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.get("/{client_id}", response_model=ClientResponse, operation_id="get_client")
async def get_client(
    client: Client = Depends(get_client_by_id),
    _current_user: User = Depends(get_current_user),
    _authorized: bool = Depends(rbac["read"]),
):
    return ClientResponse.model_validate(client)


@router.put("/{client_id}/revoke", operation_id="revoke_client")
async def revoke_client(
    client: Client = Depends(get_client_by_id),
    current_user: User = Depends(get_current_user),
    _authorized: bool = Depends(rbac["update"]),
    db: Session = Depends(get_db),
):
    try:
        RevokeClientCommand(db).execute(client.id, current_user)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"message": "Client revoked successfully"}


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_client",
)
async def delete_client(
    client: Client = Depends(get_client_by_id),
    current_user: User = Depends(get_current_user),
    _authorized: bool = Depends(rbac["delete"]),
    db: Session = Depends(get_db),
):
    try:
        success = DeleteClientCommand(db).execute(client.id, current_user)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
