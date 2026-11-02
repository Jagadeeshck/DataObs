"""Built-in quality check templates.

A *template* is a ready-to-use starting point for one of the registered built-in
checks (see :mod:`src.quality.checks.registry`). It does not introduce a new
check implementation — it describes an existing ``check_type`` together with the
configuration fields an operator must (or may) supply, and sensible defaults.

Templates let the Console and API offer a curated catalog ("freshness",
"row count", "null rate", "schema drift", "uniqueness", "distribution shift")
instead of forcing operators to hand-author raw check configuration. Every
template maps to a check type that already exists in ``CHECK_REGISTRY``; the
catalog is validated against that registry so a template can never reference an
unsupported check.

Honesty semantics: a template is a *suggestion*, not a guarantee. Fields marked
``required=True`` have no default and must be provided by the operator before the
check can run; the catalog never fabricates values (such as a concrete dataset or
column) that the operator has not chosen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .registry import supported_check_types

# Stable identifiers for the six built-in templates. These are part of the API
# contract consumed by the Console; do not rename without a coordinated change.
FRESHNESS = "freshness"
ROW_COUNT = "row_count"
NULL_RATE = "null_rate"
SCHEMA_DRIFT = "schema_drift"
UNIQUENESS = "uniqueness"
DISTRIBUTION_SHIFT = "distribution_shift"


@dataclass(frozen=True)
class TemplateField:
    """One configuration field exposed by a template."""

    name: str
    type: str  # "string" | "number" | "boolean" | "array"
    required: bool = False
    description: str = ""
    default: Any = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "description": self.description,
        }
        if not self.required:
            payload["default"] = self.default
        return payload


@dataclass(frozen=True)
class CheckTemplate:
    """A curated, named starting point for a built-in check type."""

    id: str
    title: str
    description: str
    check_type: str
    category: str
    fields: tuple[TemplateField, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "check_type": self.check_type,
            "category": self.category,
            "fields": [f.to_dict() for f in self.fields],
        }


_DATASET_FIELD = TemplateField(
    name="dataset",
    type="string",
    required=True,
    description="Fully-qualified table or view the check runs against.",
)
_SEVERITY_FIELD = TemplateField(
    name="severity",
    type="string",
    required=False,
    default="high",
    description="Severity assigned to a finding when the check fails.",
)


_TEMPLATES: tuple[CheckTemplate, ...] = (
    CheckTemplate(
        id=FRESHNESS,
        title="Freshness anomaly",
        description=(
            "Flag datasets whose update age deviates from its learned baseline using "
            "native Elasticsearch ML anomaly detection. Requires an ML anomaly job id."
        ),
        check_type="ml_anomaly",
        category="freshness",
        fields=(
            _DATASET_FIELD,
            TemplateField(
                name="ml_job_id",
                type="string",
                required=True,
                description="Elasticsearch anomaly-detection job id supplying freshness-age records.",
            ),
            TemplateField(
                name="record_score_threshold",
                type="number",
                required=False,
                default=75,
                description="Minimum ES anomaly record score (0-100) that flags a finding.",
            ),
            _SEVERITY_FIELD,
        ),
    ),
    CheckTemplate(
        id=ROW_COUNT,
        title="Row count range",
        description="Fail when a table's row count falls outside an expected minimum/maximum.",
        check_type="row_count",
        category="volume",
        fields=(
            _DATASET_FIELD,
            TemplateField(
                name="min_rows",
                type="number",
                required=False,
                default=None,
                description="Minimum acceptable row count. Omit to skip the lower bound.",
            ),
            TemplateField(
                name="max_rows",
                type="number",
                required=False,
                default=None,
                description="Maximum acceptable row count. Omit to skip the upper bound.",
            ),
            _SEVERITY_FIELD,
        ),
    ),
    CheckTemplate(
        id=NULL_RATE,
        title="Null rate",
        description="Fail when the null percentage in one or more columns exceeds a ceiling.",
        check_type="null_check",
        category="completeness",
        fields=(
            _DATASET_FIELD,
            TemplateField(
                name="columns",
                type="array",
                required=True,
                description="Columns whose null rate is evaluated.",
            ),
            TemplateField(
                name="max_null_pct",
                type="number",
                required=False,
                default=0.0,
                description="Maximum tolerated null percentage per column (0 = no nulls allowed).",
            ),
            _SEVERITY_FIELD,
        ),
    ),
    CheckTemplate(
        id=SCHEMA_DRIFT,
        title="Schema drift",
        description="Detect breaking schema changes (removed columns, type changes) against the stored baseline.",
        check_type="schema_change",
        category="schema",
        fields=(
            _DATASET_FIELD,
            TemplateField(
                name="alert_on",
                type="array",
                required=False,
                default=["column_removed", "type_changed"],
                description="Change types that raise a finding: column_removed, type_changed, column_added.",
            ),
            TemplateField(
                name="severity",
                type="string",
                required=False,
                default="critical",
                description="Severity assigned to a finding when the check fails.",
            ),
        ),
    ),
    CheckTemplate(
        id=UNIQUENESS,
        title="Uniqueness",
        description="Fail when a column (or column combination) contains duplicate values.",
        check_type="uniqueness",
        category="validity",
        fields=(
            _DATASET_FIELD,
            TemplateField(
                name="columns",
                type="array",
                required=True,
                description="Column(s) that must be unique together.",
            ),
            TemplateField(
                name="severity",
                type="string",
                required=False,
                default="critical",
                description="Severity assigned to a finding when the check fails.",
            ),
        ),
    ),
    CheckTemplate(
        id=DISTRIBUTION_SHIFT,
        title="Distribution shift",
        description="Detect statistical drift in a numeric column against a rolling, self-calibrating baseline.",
        check_type="distribution_drift",
        category="distribution",
        fields=(
            _DATASET_FIELD,
            TemplateField(
                name="column",
                type="string",
                required=True,
                description="Numeric column whose distribution is monitored.",
            ),
            TemplateField(
                name="z_score_threshold",
                type="number",
                required=False,
                default=3.0,
                description="Z-score at or above which drift is flagged.",
            ),
            _SEVERITY_FIELD,
        ),
    ),
)


def _validate_catalog() -> None:
    """Fail fast if a template references an unsupported check type.

    This keeps the curated catalog honest: it can only ever surface checks that
    are actually registered and runnable.
    """

    supported = set(supported_check_types())
    for template in _TEMPLATES:
        if template.check_type not in supported:
            raise ValueError(
                f"template {template.id!r} references unsupported check_type "
                f"{template.check_type!r}; supported: {', '.join(sorted(supported))}"
            )
    ids = [template.id for template in _TEMPLATES]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate template id in quality check template catalog")


_validate_catalog()


def list_templates() -> list[CheckTemplate]:
    """Return the built-in quality check templates in stable display order."""

    return list(_TEMPLATES)


def template_catalog() -> list[dict[str, Any]]:
    """Return the templates as serializable dicts for the API/Console."""

    return [template.to_dict() for template in _TEMPLATES]


def get_template(template_id: str) -> CheckTemplate | None:
    """Return the template with *template_id*, or ``None`` if unknown."""

    return next((template for template in _TEMPLATES if template.id == template_id), None)
