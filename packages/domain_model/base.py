from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .pillar import Pillar, parse_pillar


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DomainModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid", populate_by_name=True)


class ProductEntity(DomainModel):
    id: str
    tenant_id: str
    environment: str = "default"
    schema_version: str = "v1"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    source_id: Optional[str] = None
    integration_id: Optional[str] = None
    owner_team: Optional[str] = None
    business_service: Optional[str] = None
    pillar: Pillar = Pillar.DATA
    status: str = "active"
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None

    @field_validator("pillar", mode="before")
    @classmethod
    def _pillar(cls, value):
        return parse_pillar(value)
