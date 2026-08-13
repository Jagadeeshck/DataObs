from datetime import datetime, timedelta, timezone

import pytest

from packages.domain_model.incident import Incident, Severity
from services.incident_manager.post_incident.analytics import build_projection, state_durations
from services.incident_manager.post_incident.models import (
    ReviewSections,
    ReviewStatus,
    RootCauseClassification,
    RootCauseEntry,
    review_identity,
)
from services.incident_manager.post_incident.service import (
    InMemoryPostIncidentRepository,
    PostIncidentService,
    ReviewImmutable,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def incident(**kw):
    values = dict(
        id="i1",
        tenant_id="t",
        environment="prod",
        deduplication_key="d",
        severity=Severity.CRITICAL,
        opened_at=NOW,
        first_observed_at=NOW - timedelta(minutes=1),
        acknowledged_at=NOW + timedelta(minutes=2),
        resolved_at=NOW + timedelta(minutes=10),
        closed_at=NOW + timedelta(minutes=12),
        seq_no=3,
        primary_term=1,
    )
    values.update(kw)
    return Incident(**values)


def test_review_identity_is_deterministic():
    assert review_identity("t", "p", "i", 1) == review_identity("t", "p", "i", 1)


def test_review_creation_is_idempotent():
    s = PostIncidentService(InMemoryPostIncidentRepository())
    assert (
        s.create(incident(), owner="u", evidence_cutoff=NOW, timeline_event_ids=[]).review_id
        == s.create(incident(), owner="u", evidence_cutoff=NOW, timeline_event_ids=[]).review_id
    )


def test_completed_review_is_immutable():
    s = PostIncidentService(InMemoryPostIncidentRepository())
    r = s.create(incident(), owner="u", evidence_cutoff=NOW, timeline_event_ids=[])
    r = s.transition("t", "prod", r.review_id, ReviewStatus.IN_REVIEW, actor="u", expected_revision=1)
    r = s.transition("t", "prod", r.review_id, ReviewStatus.COMPLETED, actor="u", expected_revision=2)
    with pytest.raises(ReviewImmutable):
        s.update_sections("t", "prod", r.review_id, ReviewSections(summary="x"), expected_revision=3)


def test_refresh_evidence_preserves_human_sections():
    s = PostIncidentService(InMemoryPostIncidentRepository())
    r = s.create(incident(), owner="u", evidence_cutoff=NOW, timeline_event_ids=[])
    r = s.update_sections("t", "prod", r.review_id, ReviewSections(summary="human"), expected_revision=1)
    r = s.refresh_evidence(
        "t",
        "prod",
        r.review_id,
        incident_revision="4:1",
        evidence_cutoff=NOW,
        timeline_event_ids=["e"],
        expected_revision=2,
    )
    assert r.sections.summary == "human"


def test_hypothesis_does_not_become_confirmed_automatically():
    assert (
        RootCauseEntry(
            classification=RootCauseClassification.HYPOTHESIS, summary="possible", created_at=NOW
        ).classification
        == RootCauseClassification.HYPOTHESIS
    )


def test_metrics_and_missing_semantics():
    p = build_projection(incident(), [], computed_at=NOW + timedelta(minutes=15))
    assert (
        p["time_to_acknowledge"]["value_ms"] == 120000
        and p["time_to_resolve"]["value_ms"] == 600000
        and p["time_to_close"]["value_ms"] == 720000
        and p["signal_to_incident"]["value_ms"] == 60000
    )
    q = build_projection(incident(acknowledged_at=None, resolved_at=None), [], computed_at=NOW)
    assert (
        q["time_to_acknowledge"]["status"] == "unavailable"
        and q["time_to_acknowledge"]["value_ms"] is None
        and q["time_to_resolve"]["value_ms"] is None
    )


def test_state_duration_multiple_segments_and_special_states():
    ev = []
    for n, (m, state) in enumerate(
        [
            (0, "investigating"),
            (2, "mitigating"),
            (4, "investigating"),
            (5, "waiting_for_approval"),
            (8, "monitoring_recovery"),
            (10, "resolved"),
        ]
    ):
        ev.append({"event_id": str(n), "occurred_at": NOW + timedelta(minutes=m), "state": state})
    d = state_durations(ev)
    assert d["investigating"] == 180000 and d["waiting_for_approval"] == 180000 and d["monitoring_recovery"] == 120000


def test_reopen_count_from_timeline():
    events = [
        {"event_id": str(i), "occurred_at": NOW + timedelta(minutes=i), "event_type": "incident_reopened"}
        for i in (11, 13)
    ]
    assert build_projection(incident(), events, computed_at=NOW)["reopen_count"] == 2
