from packages.elastic_store.manifest import migrations
from packages.elastic_store.registry import (
    _mapping_update_type_matches,
    _selected_migrations,
)


def test_default_selection_is_full_and_stable():
    assert [item.migration_id for item in _selected_migrations()] == [item.migration_id for item in migrations()]
    assert _selected_migrations() == _selected_migrations()


def test_apply_through_0016_is_dependency_complete_prefix():
    selected = _selected_migrations("0016_data_product_membership_dependency_runtime")
    assert selected[-1].migration_id == "0016_data_product_membership_dependency_runtime"
    selected_ids = {item.migration_id for item in selected}
    assert all(set(item.dependencies) <= selected_ids for item in selected)
    assert migrations()[-1] not in selected


def test_unknown_apply_boundary_fails_closed():
    try:
        _selected_migrations("9999_unknown")
    except ValueError as exc:
        assert "Unknown migration id" in str(exc)
    else:
        raise AssertionError("unknown migration boundary was accepted")


def test_released_decision_reason_collision_is_compatible():
    assert _mapping_update_type_matches(
        "dataobs-data-product-membership-decisions-v1",
        "reason",
        {"type": "match_only_text"},
        {"type": "keyword"},
    )


def test_unknown_mapping_conflicts_remain_fail_closed():
    expected = {"type": "match_only_text"}
    installed = {"type": "keyword"}
    assert not _mapping_update_type_matches("dataobs-other-v1", "reason", expected, installed)
    assert not _mapping_update_type_matches(
        "dataobs-data-product-membership-decisions-v1",
        "other_reason",
        expected,
        installed,
    )
