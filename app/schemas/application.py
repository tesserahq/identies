"""Pydantic schemas for Application."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ApplicationBase(BaseModel):
    """Base application model containing common application attributes."""

    name: str
    """Name of the application."""

    url: Optional[str] = None
    """URL of the application."""

    logo: Optional[str] = None
    """URL or path to the application logo."""

    description: Optional[str] = None
    """Description of the application."""


class ApplicationCreate(ApplicationBase):
    """Schema for creating a new application. Inherits all fields from ApplicationBase."""

    pass


class ApplicationUpdate(BaseModel):
    """Schema for updating an existing application. All fields are optional."""

    name: Optional[str] = None
    """Updated name of the application."""

    url: Optional[str] = None
    """Updated URL of the application."""

    logo: Optional[str] = None
    """Updated logo URL or path."""

    description: Optional[str] = None
    """Updated description of the application."""


class ApplicationInDB(ApplicationBase):
    """Schema representing an application as stored in the database."""

    id: UUID
    """Unique identifier for the application in the database."""

    created_at: datetime
    """Timestamp when the application record was created."""

    updated_at: datetime
    """Timestamp when the application record was last updated."""

    model_config = ConfigDict(from_attributes=True)


class Application(ApplicationInDB):
    """Schema for application data returned in API responses."""

    pass
