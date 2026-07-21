from __future__ import annotations

import re
from datetime import timedelta

from packages.domain_model.data_product import DataProductSLODefinition


def validate_slo(definition: DataProductSLODefinition) -> None:
    match = re.fullmatch(r"(\d+)([mhd])", definition.window)
    if not match:
        raise ValueError("window must be a bounded duration such as 30m, 24h, or 7d")
    value, unit = int(match.group(1)), match.group(2)
    duration = timedelta(**{{"m": "minutes", "h": "hours", "d": "days"}[unit]: value})
    if duration <= timedelta(0) or duration > timedelta(days=365):
        raise ValueError("SLO window outside bounds")
    if not definition.source_monitor_ids:
        raise ValueError("an SLO requires at least one compatible source monitor")
