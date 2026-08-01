from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from packages.domain_model.incident import Incident


@dataclass(frozen=True)
class IncidentInboxFilters:
    state: str | None = None
    severity: str | None = None
    owner: str | None = None
    business_service: str | None = None
    asset: str | None = None
    unassigned: bool = False
    opened_from: datetime | None = None
    opened_to: datetime | None = None
    observed_from: datetime | None = None
    observed_to: datetime | None = None
    search: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "IncidentInboxFilters":
        return cls(**{key: value[key] for key in cls.__dataclass_fields__ if key in value})

    def fingerprint_value(self) -> dict[str, Any]:
        return {key: item.isoformat() if isinstance(item, datetime) else item for key, item in self.__dict__.items()}


@dataclass
class IncidentInboxPage:
    items: list[Incident]
    sort_values: list[Any] | None
    pit_id: str | None


@dataclass
class TimelinePage:
    items: list[dict[str, Any]]
    sort_values: list[Any] | None
