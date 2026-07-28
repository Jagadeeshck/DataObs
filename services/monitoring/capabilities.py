"""Canonical, fail-closed Data Quality Monitoring v1 capability registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from packages.domain_model.monitor import MonitorDefinition, MonitorType, ThresholdMode


@dataclass(frozen=True)
class MonitorCapability:
    monitor_type: str
    display_name: str
    description: str
    target_requirements: tuple[str, ...]
    supported_data_sources: tuple[str, ...]
    required_parameters: tuple[str, ...]
    threshold_modes: tuple[str, ...]
    baseline_support: bool
    result_unit: str
    provider: str
    permissions_required: tuple[str, ...] = ("quality:read", "quality:write", "quality:execute")
    cost_classification: str = "low"
    executable: bool = True

    def document(self) -> dict:
        value = asdict(self)
        value["capability_state"] = "supported" if self.executable else "unsupported"
        return value


def _cap(
    monitor_type: str,
    name: str,
    requirements: tuple[str, ...],
    parameters: tuple[str, ...],
    unit: str,
    *,
    baseline: bool = True,
    cost: str = "low",
) -> MonitorCapability:
    modes = ("fixed", "learned", "hybrid") if baseline else ("fixed",)
    return MonitorCapability(
        monitor_type,
        name,
        f"Production {name.lower()} observation.",
        requirements,
        ("postgresql",),
        parameters,
        modes,
        baseline,
        unit,
        "postgresql_aggregate",
        cost_classification=cost,
    )


CAPABILITIES = {
    "freshness": _cap("freshness", "Freshness", ("table", "timestamp_column"), ("timezone",), "seconds"),
    "volume": _cap("volume", "Volume", ("table",), ("aggregation",), "rows"),
    "schema_change": _cap(
        "schema_change", "Schema change", ("table",), ("change_classifications",), "changes", baseline=False
    ),
    "field_null_rate": _cap("field_null_rate", "Field null rate", ("table", "column"), (), "percent"),
    "field_unique_rate": _cap("field_unique_rate", "Field unique rate", ("table", "columns"), (), "ratio"),
    "field_distribution": _cap(
        "field_distribution", "Field distribution", ("table", "column"), ("comparison_method",), "score", cost="medium"
    ),
    "field_range": _cap("field_range", "Field range", ("table", "column"), (), "value"),
    "validation": _cap("validation", "Validation", ("table",), ("aggregate_expression",), "boolean"),
    "custom_sql_aggregate": _cap(
        "custom_sql_aggregate", "Custom SQL aggregate", ("table",), ("aggregate_expression",), "value", cost="medium"
    ),
}


def capability_documents() -> list[dict]:
    supported = [CAPABILITIES[key].document() for key in sorted(CAPABILITIES)]
    unsupported = []
    for item in MonitorType:
        if item.value not in CAPABILITIES:
            unsupported.append({"monitor_type": item.value, "capability_state": "unsupported", "executable": False})
    return supported + unsupported


def validate_monitor_definition(definition: MonitorDefinition) -> None:
    capability = CAPABILITIES.get(str(definition.monitor_type))
    if capability is None:
        raise ValueError(f"monitor type is not executable in Data Quality Monitoring v1: {definition.monitor_type}")
    target = definition.target
    if not target.asset_id and not (target.schema_name and target.table_name):
        raise ValueError("monitor target requires an asset_id or schema and table")
    if "timestamp_column" in capability.target_requirements and not target.timestamp_column:
        raise ValueError("freshness monitor requires timestamp_column")
    if "column" in capability.target_requirements and len(target.columns) != 1:
        raise ValueError("monitor requires exactly one target column")
    if "columns" in capability.target_requirements and not target.columns:
        raise ValueError("monitor requires one or more target columns")
    missing = [name for name in capability.required_parameters if name not in target.parameters]
    if missing:
        raise ValueError("missing required monitor parameters: " + ", ".join(missing))
    if definition.threshold.mode in {ThresholdMode.LEARNED, ThresholdMode.HYBRID} and definition.baseline is None:
        raise ValueError("learned and hybrid thresholds require a baseline policy")
    if definition.monitor_type == MonitorType.FIELD_NULL_RATE:
        bounds = (definition.threshold.minimum, definition.threshold.maximum)
        if any(value is not None and not 0 <= value <= 100 for value in bounds):
            raise ValueError("null-rate thresholds must be percentages between 0 and 100")
