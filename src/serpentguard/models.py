"""Shared Pydantic model foundation.

Domain models for parsed Serpent input and findings are intentionally deferred to a
later implementation phase.
"""

from pydantic import BaseModel, ConfigDict


class SerpentGuardModel(BaseModel):
    """Strict base class for future structured SerpentGuard models."""

    model_config = ConfigDict(extra="forbid")
