from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class SeasonalCohort:
    key: str
    reason: str


def select_cohort(at: datetime, dimensions: list[str], timezone: str = "UTC") -> SeasonalCohort:
    local = at.astimezone(ZoneInfo(timezone))
    parts: list[str] = []
    reasons: list[str] = []
    if "day_of_week" in dimensions or "weekly" in dimensions:
        parts.append(f"dow={local.weekday()}")
        reasons.append("matched local day of week")
    if "hour_of_day" in dimensions:
        parts.append(f"hour={local.hour}")
        reasons.append("matched local hour")
    if not parts:
        return SeasonalCohort("all", "no seasonality configured")
    return SeasonalCohort(";".join(parts), "; ".join(reasons))
