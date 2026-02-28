"""Tests for ApplicationService."""

import pytest
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.services.application_service import ApplicationService


def test_create_application(db: Session, sample_application_data):
    """Test creating a new application."""
    application_create = ApplicationCreate(**sample_application_data)
    application = ApplicationService(db).create_application(application_create)

    assert application.id is not None
    assert application.name == sample_application_data["name"]
    assert application.url == sample_application_data["url"]
    assert application.logo == sample_application_data["logo"]
    assert application.description == sample_application_data["description"]
    assert application.created_at is not None
    assert application.updated_at is not None


def test_get_application(db: Session, sample_application):
    """Test getting an application by ID."""
    retrieved = ApplicationService(db).get_application(sample_application.id)

    assert retrieved is not None
    assert retrieved.id == sample_application.id
    assert retrieved.name == sample_application.name
    assert retrieved.url == sample_application.url


def test_get_applications(db: Session, sample_application):
    """Test getting all applications with pagination."""
    applications = ApplicationService(db).get_applications()

    assert len(applications) >= 1
    assert any(a.id == sample_application.id for a in applications)


def test_get_applications_with_pagination(db: Session, sample_application):
    """Test getting applications with pagination parameters."""
    another = Application(
        name="Another App",
        url="https://another.com",
        description="Another app",
    )
    db.add(another)
    db.commit()
    db.refresh(another)

    applications = ApplicationService(db).get_applications(skip=0, limit=1)
    assert len(applications) == 1

    applications = ApplicationService(db).get_applications(skip=1, limit=1)
    assert len(applications) == 1


def test_update_application(db: Session, sample_application):
    """Test updating an application."""
    update_data = {
        "name": "Updated App",
        "url": "https://updated.com",
        "logo": "https://updated.com/logo.png",
        "description": "Updated description",
    }
    application_update = ApplicationUpdate(**update_data)

    updated = ApplicationService(db).update_application(
        sample_application.id, application_update
    )

    assert updated is not None
    assert updated.id == sample_application.id
    assert updated.name == update_data["name"]
    assert updated.url == update_data["url"]
    assert updated.logo == update_data["logo"]
    assert updated.description == update_data["description"]


def test_update_application_partial(db: Session, sample_application):
    """Test partial update of an application."""
    update_data = {"description": "Updated description only"}
    application_update = ApplicationUpdate(**update_data)

    updated = ApplicationService(db).update_application(
        sample_application.id, application_update
    )

    assert updated is not None
    assert updated.id == sample_application.id
    assert updated.name == sample_application.name
    assert updated.url == sample_application.url
    assert updated.description == update_data["description"]


def test_delete_application(db: Session, sample_application):
    """Test deleting an application."""
    service = ApplicationService(db)

    success = service.delete_application(sample_application.id)

    assert success is True
    assert service.get_application(sample_application.id) is None


def test_application_not_found_cases(db: Session):
    """Test various not found cases."""
    service = ApplicationService(db)
    non_existent_id = uuid4()

    assert service.get_application(non_existent_id) is None

    update_data = {"description": "Updated"}
    application_update = ApplicationUpdate(**update_data)
    assert service.update_application(non_existent_id, application_update) is None

    assert service.delete_application(non_existent_id) is False


def test_search_applications(db: Session, sample_application):
    """Test search method with dynamic filters."""
    filters = {"name": {"operator": "ilike", "value": f"%{sample_application.name}%"}}
    results = ApplicationService(db).search(filters)

    assert isinstance(results, list)
    assert any(a.id == sample_application.id for a in results)

    filters = {"name": sample_application.name}
    results = ApplicationService(db).search(filters)
    assert len(results) >= 1

    if sample_application.description:
        partial_desc = sample_application.description[:10]
        filters = {"description": {"operator": "ilike", "value": f"%{partial_desc}%"}}
        results = ApplicationService(db).search(filters)
        assert len(results) >= 1


def test_create_application_without_optional_fields(db: Session):
    """Test creating an application without optional fields."""
    application_data = {"name": "Minimal App"}

    application_create = ApplicationCreate(**application_data)
    application = ApplicationService(db).create_application(application_create)

    assert application.id is not None
    assert application.name == "Minimal App"
    assert application.url is None
    assert application.logo is None
    assert application.description is None


def test_get_applications_query_with_search(db: Session, sample_application):
    """Test get_applications_query with search filter."""
    service = ApplicationService(db)

    query = service.get_applications_query(q=sample_application.name)
    results = query.all()
    assert any(a.id == sample_application.id for a in results)

    query = service.get_applications_query(q="nonexistent")
    results = query.all()
    assert len(results) == 0
