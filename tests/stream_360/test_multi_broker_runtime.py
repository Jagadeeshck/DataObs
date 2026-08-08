from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services.stream_observer.multi_broker_runtime import MultiBrokerRuntime
from services.stream_observer.repository import FenceRejected, canonical_evidence_id, checkpoint_id


def observation(**overrides):
    value = {
        "tenant_id": "tenant-a",
        "environment": "prod",
        "messaging_system": "sqs",
        "provider_account_scope": "123",
        "cloud_region_or_location": "us-east-1",
        "cloud": "aws",
        "resource_kind": "queue",
        "provider_resource_id": "arn:aws:sqs:us-east-1:123:orders",
        "name": "orders",
        "observed_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "collection_method": "provider_metrics",
        "source_integration": "aws-main",
    }
    value.update(overrides)
    return value


class Repository:
    def __init__(self):
        self.evidence = set()
        self.projections = {}

    def append(self, family, document):
        key = canonical_evidence_id(document, family)
        fresh = key not in self.evidence
        self.evidence.add(key)
        return fresh

    def project(self, family, document, *, fencing_token):
        current = self.projections.get(document["resource_id"])
        if current and current[0] > fencing_token:
            raise FenceRejected("stale_fencing_token")
        self.projections[document["resource_id"]] = (fencing_token, document)


def test_evidence_and_checkpoint_ids_are_deterministic_and_scoped():
    doc = observation(resource_id="canonical")
    doc["source_integration"] = "aws-main"
    assert canonical_evidence_id(doc, "resource") == canonical_evidence_id(dict(doc), "resource")
    scope = {
        "tenant_id": "a",
        "environment": "prod",
        "provider_integration": "i",
        "messaging_system": "sqs",
        "observation_family": "inventory",
        "resource_scope": "account",
    }
    assert checkpoint_id(scope) != checkpoint_id(scope | {"tenant_id": "b"})


def test_runtime_replay_is_idempotent_and_rejects_cross_scope():
    repo = Repository()
    runtime = MultiBrokerRuntime(repo)  # type: ignore[arg-type]
    first = runtime.run(
        [observation(), observation(tenant_id="tenant-b")], tenant_id="tenant-a", environment="prod", fencing_token=10
    )
    second = runtime.run([observation()], tenant_id="tenant-a", environment="prod", fencing_token=10)
    assert (first.read, first.normalized, first.rejected, first.projected, first.duplicates) == (2, 1, 1, 1, 0)
    assert second.duplicates == 1
    assert len(repo.evidence) == 1


def test_fencing_rejects_expired_worker_and_accepts_successor():
    repo = Repository()
    runtime = MultiBrokerRuntime(repo)  # type: ignore[arg-type]
    runtime.run([observation()], tenant_id="tenant-a", environment="prod", fencing_token=10)
    runtime.run([observation()], tenant_id="tenant-a", environment="prod", fencing_token=11)
    with pytest.raises(FenceRejected, match="stale_fencing_token"):
        runtime.run([observation()], tenant_id="tenant-a", environment="prod", fencing_token=10)
