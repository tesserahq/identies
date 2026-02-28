"""Service for Application CRUD operations."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Query, Session

from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.utils.db.filtering import apply_filters


class ApplicationService:
    """Service for application CRUD and search."""

    def __init__(self, db: Session):
        self.db = db

    def get_application(self, application_id: UUID) -> Optional[Application]:
        """Get a single application by ID."""
        return (
            self.db.query(Application).filter(Application.id == application_id).first()
        )

    def get_applications(self, skip: int = 0, limit: int = 100) -> List[Application]:
        """Get a list of applications with pagination."""
        return self.db.query(Application).offset(skip).limit(limit).all()

    def get_applications_query(self, q: Optional[str] = None) -> Query:
        """Query for applications (for pagination). Optionally filter by name or description."""
        query = self.db.query(Application).order_by(Application.created_at.desc())
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            query = query.filter(
                (Application.name.ilike(pattern))
                | (Application.description.ilike(pattern))
            )
        return query

    def create_application(self, data: ApplicationCreate) -> Application:
        """Create a new application."""
        application = Application(**data.model_dump())
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    def update_application(
        self, application_id: UUID, data: ApplicationUpdate
    ) -> Optional[Application]:
        """Update an existing application."""
        application = self.get_application(application_id)
        if application:
            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(application, key, value)
            self.db.commit()
            self.db.refresh(application)
        return application

    def delete_application(self, application_id: UUID) -> bool:
        """Delete an application by ID."""
        application = self.get_application(application_id)
        if application:
            self.db.delete(application)
            self.db.commit()
            return True
        return False

    def search(self, filters: dict) -> List[Application]:
        """Search applications based on dynamic filter criteria."""
        query = self.db.query(Application)
        query = apply_filters(query, Application, filters)
        return query.all()
