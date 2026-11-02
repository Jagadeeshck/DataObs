from packages.pathways.stream_templates import (
    STREAM_DETECTOR_TEMPLATES,
    get_template,
    list_templates,
)
from packages.streaming.intelligence import CAPABILITIES, METHODS, DetectorDefinition


def test_every_template_descriptor_is_capability_backed():
    assert STREAM_DETECTOR_TEMPLATES, "templates must not be empty"
    for template in STREAM_DETECTOR_TEMPLATES:
        capability = CAPABILITIES.get(template.resource_type)
        assert capability is not None, template.template_id
        assert template.metric in capability, template.template_id
        assert template.method in METHODS, template.template_id
        assert template.direction in {"high", "low", "both"}, template.template_id
        assert template.applicable is True
        assert template.capability_status == "supported"


def test_templates_cover_the_three_authoring_categories():
    categories = {template.category for template in STREAM_DETECTOR_TEMPLATES}
    assert categories == {"freshness", "lag", "throughput"}


def test_template_fields_build_a_valid_detector_definition():
    # A preset must be a safe starting point: pre-filled fields plus caller-supplied
    # identity must construct a real DetectorDefinition without validation errors.
    for template in STREAM_DETECTOR_TEMPLATES:
        fields = template.detector_fields()
        definition = DetectorDefinition(
            detector_id="det-1",
            tenant_id="tenant-a",
            environment="prod",
            resource_id="resource-1",
            **fields,
        )
        assert definition.enabled is False  # a template never auto-activates
        assert definition.resource_type == template.resource_type
        assert definition.metric == template.metric


def test_list_and_filter_are_deterministic_and_scoped_by_category():
    assert list_templates() == list(STREAM_DETECTOR_TEMPLATES)
    lag_only = list_templates("lag")
    assert lag_only and all(template.category == "lag" for template in lag_only)
    # An unknown category yields an empty list, never a fabricated template.
    assert list_templates("does-not-exist") == []


def test_get_template_returns_none_for_unknown_id():
    known = STREAM_DETECTOR_TEMPLATES[0]
    assert get_template(known.template_id) is known
    assert get_template("missing") is None


def test_descriptor_shape_is_serialisable_and_honest():
    descriptor = STREAM_DETECTOR_TEMPLATES[0].descriptor()
    assert set(descriptor) == {
        "template_id",
        "title",
        "category",
        "description",
        "rationale",
        "capability_status",
        "applicable",
        "detector_fields",
    }
    assert descriptor["capability_status"] in {"supported", "unknown"}
    # Descriptor carries no measured value / no observed_at — it is intent, not data.
    assert "observed_value" not in descriptor["detector_fields"]
