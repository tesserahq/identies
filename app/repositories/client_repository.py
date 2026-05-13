from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Query, Session

from app.models.client import Client
from app.schemas.client import ClientCreate
from app.utils.security import (
    generate_client_credentials,
    hash_secret,
    verify_api_key_secret,
)


class ClientRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_client(self, client_data: ClientCreate) -> tuple[Client, str]:
        """
        Create a new OAuth client.

        Returns:
            tuple[Client, str]: The created client and the plaintext client_secret (shown once).
        """
        client_id, client_secret = generate_client_credentials()

        db_client = Client(
            client_id=client_id,
            secret_hash=hash_secret(client_secret),
            name=client_data.name,
            owner_id=client_data.owner_id,
            created_by_id=client_data.created_by_id,
        )

        self.db.add(db_client)
        self.db.commit()
        self.db.refresh(db_client)

        return db_client, client_secret

    def get_client_by_id(self, client_pk: UUID) -> Optional[Client]:
        return self.db.query(Client).filter(Client.id == client_pk).first()

    def get_client_by_client_id(self, client_id: str) -> Optional[Client]:
        return self.db.query(Client).filter(Client.client_id == client_id).first()

    def get_clients_by_owner_query(self, owner_id: UUID) -> Query:
        """
        Query for non-deleted clients owned by owner_id, newest first.
        Suitable for use with fastapi-pagination's paginate().
        """
        return (
            self.db.query(Client)
            .filter(Client.owner_id == owner_id, Client.deleted_at.is_(None))
            .order_by(Client.created_at.desc())
        )

    def list_by_owner(self, owner_id: UUID) -> List[Client]:
        return self.get_clients_by_owner_query(owner_id).all()

    def verify_client(self, client_id: str, client_secret: str) -> Optional[Client]:
        """Verify client_id + client_secret and return the client if valid."""
        client = self.get_client_by_client_id(client_id)
        if not client:
            return None
        if not client.is_valid():
            return None
        if not verify_api_key_secret(client_secret, client.secret_hash):
            return None
        return client

    def revoke_client(self, client_pk: UUID) -> bool:
        client = self.db.query(Client).filter(Client.id == client_pk).first()
        if not client:
            return False
        client.revoked = True
        self.db.commit()
        return True

    def delete_client(self, client_pk: UUID) -> bool:
        client = self.db.query(Client).filter(Client.id == client_pk).first()
        if not client:
            return False
        self.db.delete(client)
        self.db.commit()
        return True
