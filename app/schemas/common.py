"""Shared Pydantic config and utilities."""

from pydantic import BaseModel


class ORMBase(BaseModel):
    """Base schema that enables reading from SQLAlchemy ORM objects."""

    model_config = {"from_attributes": True}
