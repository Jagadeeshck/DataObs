from datetime import datetime, timedelta, timezone

import pytest

from services.asset_trust.evidence import AssetTrustEvidenceResolver, CanonicalEvidence
from services.asset_trust.runtime import FenceLost, MemoryRecalculationQueue
from services.asset_trust.scoring import deduplicate_evidence

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class Reader:
    def __init__(self, rows):
        self.rows = rows

    def read_asset_evidence(self, tenant_id, environment, asset_id):
        return self.rows


def row(ref="monitor:1", source="canonical_evaluation", dimension="freshness", derived=(), observed=NOW):
    return CanonicalEvidence(source, ref, dimension, 90, 0.9, 1, observed, derived_from=derived)


def test_resolver_normalizes_and_marks_stale_without_recalculating():
    resolver = AssetTrustEvidenceResolver(
        [Reader([row(observed=NOW - timedelta(hours=2))])], staleness_seconds={"freshness": 60}
    )
    evidence = resolver.resolve("tenant-a", "prod", "asset-1", now=NOW)
    assert evidence[0].score == 90
    assert evidence[0].status == "stale"


def test_slo_suppresses_derived_freshness_across_dimensions():
    resolver = AssetTrustEvidenceResolver(
        [
            Reader(
                [
                    row(),
                    row("slo:1", "production_slo", "slo_reliability", ("monitor:1",)),
                ]
            )
        ]
    )
    chosen = deduplicate_evidence(resolver.resolve("tenant-a", "prod", "asset-1", now=NOW))
    assert [item.evidence_ref for item in chosen] == ["slo:1"]


def test_queue_deduplicates_and_rejects_worker_that_lost_fence():
    queue = MemoryRecalculationQueue()
    queue.request("t", "prod", "a", "monitor")
    queue.request("t", "prod", "a", "slo")
    first = queue.claim("worker-1", now=NOW, lease_seconds=1)[0]
    token = first.fencing_token
    second = queue.claim("worker-2", now=NOW + timedelta(seconds=2))[0]
    with pytest.raises(FenceLost):
        queue.complete(first, "worker-1", token)
    queue.complete(second, "worker-2", second.fencing_token)
    assert queue.health()["assets_pending"] == 0
