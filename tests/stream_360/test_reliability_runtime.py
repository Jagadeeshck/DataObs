from datetime import datetime, timedelta, timezone

from packages.streaming.reliability import Definition, Observation, PreviousState, Status, evaluate
from services.kafka_observer.reliability_runtime import ReliabilityRuntime

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def definition(**changes):
    values = dict(
        id="slo-1",
        tenant_id="t",
        environment="prod",
        resource_type="consumer_group",
        resource_id="g",
        metric="consumer_lag",
        operator="gt",
        threshold=10,
        evaluation_window_seconds=300,
        enabled=True,
    )
    values.update(changes)
    return Definition(**values)


def observation(value=0, observed_at=NOW):
    return Observation(value=value, observed_at=observed_at, unit="messages", evidence_type="projection")


def test_zero_is_measured_and_not_missing():
    result = evaluate(definition(), observation(0), PreviousState(), NOW)
    assert result.observed_value == 0
    assert result.status == Status.HEALTHY


def test_missing_and_stale_are_never_healthy():
    assert evaluate(definition(), observation(None, None), PreviousState(Status.HEALTHY), NOW).status == Status.NO_DATA
    stale = evaluate(definition(), observation(0, NOW - timedelta(minutes=6)), PreviousState(), NOW)
    assert stale.status == Status.STALE


def test_equality_and_consecutive_breach_recovery_transitions():
    exact = evaluate(definition(operator="gte", required_consecutive_breaches=2), observation(10), PreviousState(), NOW)
    assert exact.status == Status.WARNING
    breach = evaluate(
        definition(operator="gte"),
        observation(10),
        PreviousState(Status.WARNING, 1, 0, NOW),
        NOW + timedelta(minutes=1),
    )
    assert breach.status == Status.BREACHING and breach.consecutive_breaches == 2
    recovering = evaluate(
        definition(),
        observation(0, NOW + timedelta(minutes=2)),
        PreviousState(Status.BREACHING, 2, 0, NOW),
        NOW + timedelta(minutes=2),
    )
    assert recovering.status == Status.RECOVERING
    healthy = evaluate(
        definition(),
        observation(0, NOW + timedelta(minutes=3)),
        PreviousState(Status.RECOVERING, 0, 1, NOW),
        NOW + timedelta(minutes=3),
    )
    assert healthy.status == Status.HEALTHY


def test_missing_policy_breach_and_ignore():
    assert (
        evaluate(
            definition(missing_data_policy="breach", required_consecutive_breaches=1),
            observation(None, None),
            PreviousState(),
            NOW,
        ).status
        == Status.BREACHING
    )
    ignored = evaluate(
        definition(missing_data_policy="ignore"), observation(None, None), PreviousState(Status.WARNING, 1), NOW
    )
    assert ignored.status == Status.WARNING


def test_estimated_latency_is_labelled_not_measured():
    d = definition(resource_type="pathway", metric="pathway_latency_p95", resource_id="p")
    o = Observation(20, NOW, "ms", "pathway_projection", latency_method="edge_estimate")
    assert evaluate(d, o, PreviousState(), NOW).latency_method == "edge_estimate"


class MemoryStore:
    def __init__(self):
        self.saved = []
        self.checkpoints = []

    def acquire(self, scope, worker, expires_at):
        return 7

    def due(self, tenant, environment, now, limit):
        return [definition()]

    def previous(self, item):
        return PreviousState()

    def persist(self, result, item, token):
        assert token == 7
        self.saved.append(result.evaluation_id)
        return True

    def checkpoint(self, item, evaluation_id, token, now):
        assert self.saved[-1] == evaluation_id
        self.checkpoints.append(evaluation_id)

    def project(self, result, item, token):
        assert self.saved[-1] == result.evaluation_id

    def signal(self, result, item, token):
        assert self.saved[-1] == result.evaluation_id

    def persist_health(self, scope, health, token):
        pass


def test_runtime_bounds_window_is_deterministic_and_persists_before_checkpoint():
    store, windows = MemoryStore(), []
    runtime = ReliabilityRuntime(store, lambda d, start, end: windows.append((start, end)) or observation(), "worker")
    first = runtime.run_once("t", "prod", NOW)[0]
    second = runtime.run_once("t", "prod", NOW)[0]
    assert first.evaluation_id == second.evaluation_id
    assert windows[0] == (NOW - timedelta(seconds=300), NOW)
    assert store.checkpoints[0] == first.evaluation_id


def test_graceful_stop_skips_due_work():
    runtime = ReliabilityRuntime(MemoryStore(), lambda *_: observation(), "worker")
    runtime.stop()
    assert runtime.run_once("t", "prod", NOW) == []
