"""Fixtures for Application tests."""

import pytest

from app.models.application import Application


@pytest.fixture
def sample_application_data(faker):
    """Sample application data for testing."""
    return {
        "name": faker.company() or "Test App",
        "url": faker.url(),
        "logo": "https://example.com/logo.png",
        "description": faker.text(max_nb_chars=100),
    }


@pytest.fixture
def sample_application(db, sample_application_data):
    """Create a sample application in the database."""
    application = Application(**sample_application_data)
    db.add(application)
    db.commit()
    db.refresh(application)
    return application
