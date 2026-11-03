"""Unit tests for the pure six-pillar Command Center aggregator.

No Elasticsearch — validates the honesty rules: unknown vs healthy, measured zero,
partial completeness, pillar health bands, and the incident priority queue.
"""

from __future__ import annotations

from services.command_center.aggregator import PILLARS, aggregate_summary


def _pillar(summary, pid):
    return next(p for p in summary["pillars"] if p["id"] == pid)


def test_six_pillars_present_in_canonical_order():
    s = aggregate_summary("acme", "production")
    ids = [p["id"] for p in s["pillars"]]
    # platform, data_pipeline, data first (implemented), then the three future pillars.
    assert ids[:3] == ["platform", "data_pipeline", "data"]
    assert set(ids) == {pid for pid, _ in PILLARS}


def test_no_sources_is_unknown_never_healthy():
    s = aggregate_summary("acme", "production")
    # Every pillar unknown; overall unknown; not complete.
    assert all(p["health"] == "unknown" for p in s["pillars"])
    assert s["overall_health"] == "unknown"
    assert s["data_status"]["complete"] is False


def test_future_pillars_are_always_unknown_not_collected():
    s = aggregate_summary(
        "acme",
        "production",
        quality=[{"status": "pass"}],
        sources_available={"quality": True},
    )
    for pid in ("finops_cost", "business", "ai_agent"):
        p = _pillar(s, pid)
        assert p["health"] == "unknown"
        assert p["coverage"] == "Not yet collected"
        assert p["issues"] is None


def test_data_pillar_healthy_when_all_checks_pass():
    s = aggregate_summary(
        "acme",
        "production",
        quality=[{"status": "pass"}, {"status": "pass"}],
        freshness=[{"status": "fresh"}],
        sources_available={"quality": True, "freshness": True},
    )
    data = _pillar(s, "data")
    assert data["health"] == "healthy"
    assert data["issues"] == 0  # measured zero, observed


def test_data_pillar_critical_when_many_failing():
    s = aggregate_summary(
        "acme",
        "production",
        quality=[{"status": "fail"}, {"status": "fail"}, {"status": "pass"}],
        sources_available={"quality": True},
    )
    data = _pillar(s, "data")
    assert data["health"] == "critical"  # 2/3 failing ≥ 0.3
    assert data["issues"] == 2


def test_measured_zero_distinct_from_unknown():
    # Observed with zero problems → healthy with issues=0 (a real zero).
    observed = aggregate_summary(
        "acme", "production", quality=[{"status": "pass"}], sources_available={"quality": True}
    )
    assert _pillar(observed, "data")["issues"] == 0
    assert _pillar(observed, "data")["health"] == "healthy"
    # Not observed → unknown with issues=None.
    missing = aggregate_summary("acme", "production", sources_available={"quality": False})
    assert _pillar(missing, "data")["issues"] is None
    assert _pillar(missing, "data")["health"] == "unknown"


def test_open_incidents_become_priority_queue_worst_first():
    s = aggregate_summary(
        "acme",
        "production",
        incidents=[
            {"incident_id": "inc-1", "title": "warn thing", "severity": "warning", "state": "open", "entity": "a"},
            {"incident_id": "inc-2", "title": "crit thing", "severity": "critical", "state": "open", "entity": "b"},
            {"incident_id": "inc-3", "title": "closed", "severity": "critical", "state": "resolved", "entity": "c"},
        ],
        sources_available={"incidents": True},
    )
    items = s["priority_items"]
    assert [i["id"] for i in items] == ["inc-2", "inc-1"]  # critical first, resolved excluded
    assert s["critical_incidents"] == 1
    assert s["affected_services"] == 2


def test_partial_completeness_when_a_source_absent():
    s = aggregate_summary(
        "acme",
        "production",
        quality=[{"status": "pass"}],
        sources_available={
            "incidents": True,
            "quality": True,
            "freshness": True,
            "lineage": True,
            "streams": False,  # one source did not answer
        },
    )
    assert s["data_status"]["complete"] is False
    assert "streams" in s["data_status"]["missing_inputs"]
    assert s["data_status"]["source_coverage"] == 80


def test_full_completeness_when_all_sources_answer():
    s = aggregate_summary(
        "acme",
        "production",
        quality=[{"status": "pass"}],
        sources_available={k: True for k in ("incidents", "quality", "freshness", "lineage", "streams")},
    )
    assert s["data_status"]["complete"] is True
    assert s["data_status"]["source_coverage"] == 100
