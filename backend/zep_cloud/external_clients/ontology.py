"""
Minimal compatibility models for dynamic ontology definitions.
"""

from pydantic import BaseModel, ConfigDict


EntityText = str


class EntityModel(BaseModel):
    """Base model for dynamic entity types."""

    model_config = ConfigDict(extra='allow')


class EdgeModel(BaseModel):
    """Base model for dynamic edge types."""

    model_config = ConfigDict(extra='allow')

