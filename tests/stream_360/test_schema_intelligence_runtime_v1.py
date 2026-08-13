from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from packages.streaming.schema_intelligence import (
    CompatibilityPolicy,
    SchemaApplicationBinding,
    SchemaIdentity,
    SchemaType,
    evaluate_schema_change,
)
from services.kafka_observer.schema_intelligence_runtime import SchemaIntelligenceRuntime, SchemaVersionObservation

NOW = datetime(2026, 8, 13, tzinfo=timezone.utc)


class MemoryRepository:
    def __init__(self):
        self.events, self.projections, self.calls = {}, {}, []
        self.token = 1

    def acquire_lease(self, *_args):
        return self.token

    def append(self, stream, identifier, document, token):
        assert token == self.token
        self.calls.append(("append", stream))
        self.events.setdefault((stream, identifier), document)
        return True

    def project(self, index, identifier, document, token):
        assert token == self.token
        self.calls.append(("project", index))
        self.projections[(index, identifier)] = document

    def checkpoint(self, tenant, environment, cursor, worker, token):
        assert token == self.token
        self.calls.append(("checkpoint", cursor))


def observation(errors=None, supported=()):
    identity = SchemaIdentity("tenant-a", "prod", "registry-a", "orders-value")
    evaluation = evaluate_schema_change(
        SchemaType.AVRO,
        CompatibilityPolicy.BACKWARD,
        {"fields": [{"name": "id", "type": "long"}]},
        {"fields": [{"name": "id", "type": "string"}]},
        hash_salt="tenant-secret",
    )
    binding = SchemaApplicationBinding(
        "consumer-a",
        "topic-a",
        identity.subject_id,
        "consumer",
        NOW,
        "consumer_instrumentation",
        1.0,
        supported_schema_versions=supported,
    )
    return SchemaVersionObservation(
        identity,
        "integration-a",
        2,
        "22",
        "AVRO",
        "fingerprint",
        "structural",
        "BACKWARD",
        NOW,
        evaluation,
        application_bindings=(binding,),
        runtime_schema_errors=errors,
    )


def test_replay_is_deterministic_and_checkpoint_is_last():
    repository = MemoryRepository()
    runtime = SchemaIntelligenceRuntime(repository, lambda *_: [observation()], "worker-a")
    first = runtime.run_once("tenant-a", "prod", now=NOW)
    second = runtime.run_once("tenant-a", "prod", now=NOW)
    assert first == second
    assert repository.calls[-1][0] == "checkpoint"
    assert len(repository.events) == 4


@pytest.mark.parametrize(
    ("errors", "supported", "expected"),
    [
        (None, (), "potentially_exposed"),
        (None, (1,), "incompatible"),
        ({"consumer-a": 3}, (), "degradation_observed"),
    ],
)
def test_consumer_exposure_requires_independent_evidence(errors, supported, expected):
    repository = MemoryRepository()
    SchemaIntelligenceRuntime(repository, lambda *_: [observation(errors, supported)], "worker-a").run_once(
        "tenant-a", "prod", now=NOW
    )
    impacts = [doc for (index, _), doc in repository.projections.items() if "impact-current" in index]
    assert impacts[0]["exposure_state"] == expected
    assert "caused by" not in str(impacts[0]).lower()


def test_collector_cannot_cross_tenant_boundary():
    repository = MemoryRepository()
    bad = observation()
    bad = SimpleNamespace(**(bad.__dict__ | {"identity": SchemaIdentity("tenant-b", "prod", "r", "s")}))
    with pytest.raises(ValueError, match="isolation"):
        SchemaIntelligenceRuntime(repository, lambda *_: [bad], "worker-a").run_once("tenant-a", "prod", now=NOW)
