"""Tests for the built-in quality check template catalog and its API route."""

from __future__ import annotations

import pytest

from src.quality.checks.registry import supported_check_types
from src.quality.checks.templates import (
    DISTRIBUTION_SHIFT,
    FRESHNESS,
    NULL_RATE,
    ROW_COUNT,
    SCHEMA_DRIFT,
    UNIQUENESS,
    get_template,
    list_templates,
    template_catalog,
)

EXPECTED_IDS = {FRESHNESS, ROW_COUNT, NULL_RATE, SCHEMA_DRIFT, UNIQUENESS, DISTRIBUTION_SHIFT}


def test_catalog_exposes_six_templates_with_stable_ids():
    templates = list_templates()
    assert {t.id for t in templates} == EXPECTED_IDS
    assert len(templates) == 6
    # Stable display order is preserved between calls.
    assert [t.id for t in list_templates()] == [t.id for t in templates]


def test_every_template_maps_to_a_registered_check_type():
    supported = set(supported_check_types())
    for template in list_templates():
        assert template.check_type in supported, template.id


def test_required_fields_have_no_default_and_optional_fields_do():
    for template in list_templates():
        for field in template.fields:
            if field.required:
                payload = field.to_dict()
                # A required field never advertises a fabricated default value.
                assert "default" not in payload, (template.id, field.name)
            else:
                assert "default" in field.to_dict(), (template.id, field.name)


def test_dataset_is_required_on_every_template():
    for template in list_templates():
        dataset = next((f for f in template.fields if f.name == "dataset"), None)
        assert dataset is not None and dataset.required, template.id


def test_freshness_template_requires_ml_job_id():
    freshness = get_template(FRESHNESS)
    assert freshness is not None
    assert freshness.check_type == "ml_anomaly"
    required = {f.name for f in freshness.fields if f.required}
    assert "ml_job_id" in required


def test_get_template_returns_none_for_unknown_id():
    assert get_template("does-not-exist") is None


def test_template_catalog_is_json_serializable_dicts():
    catalog = template_catalog()
    assert isinstance(catalog, list)
    for entry in catalog:
        assert set(entry) == {"id", "title", "description", "check_type", "category", "fields"}
        assert isinstance(entry["fields"], list)


def test_route_handler_returns_catalog_with_complete_evidence():
    """The templates route reports a static catalog with complete, honest evidence."""
    from src.api.monitor_routes import quality_templates

    class _Req:
        class state:  # noqa: N801 - mimic request.state attribute access
            request_id = "req-templates-1"

        headers: dict[str, str] = {}

    payload = quality_templates(_Req())
    assert payload["schema_version"] == "v1"
    assert {entry["id"] for entry in payload["items"]} == EXPECTED_IDS
    # Static catalog carries no missing/stale operational evidence.
    assert payload["data_status"] == "complete"
    assert payload["missing_inputs"] == []
    assert payload["warnings"] == []
    assert payload["source_coverage"] == ["quality_check_templates"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
