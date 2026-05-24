from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock


_SPARK_DIR = Path(__file__).resolve().parents[1] / "integrations" / "spark"
if str(_SPARK_DIR) not in sys.path:
    sys.path.insert(0, str(_SPARK_DIR))

import glue_job_monitor as gm  # noqa: E402


class _FakeInstrument:
    def __init__(self):
        self.calls = []

    def set(self, value, attributes=None):
        self.calls.append(("set", value, attributes or {}))

    def record(self, value, attributes=None):
        self.calls.append(("record", value, attributes or {}))

    def add(self, value, attributes=None):
        self.calls.append(("add", value, attributes or {}))


class _FakeMeter:
    def __init__(self):
        self.created = []
        self.by_name = {}

    def create_gauge(self, name, **kwargs):
        inst = _FakeInstrument()
        self.created.append(("gauge", name))
        self.by_name[name] = inst
        return inst

    def create_histogram(self, name, **kwargs):
        inst = _FakeInstrument()
        self.created.append(("histogram", name))
        self.by_name[name] = inst
        return inst

    def create_counter(self, name, **kwargs):
        inst = _FakeInstrument()
        self.created.append(("counter", name))
        self.by_name[name] = inst
        return inst


class _FakeSpan:
    def __init__(self):
        self.statuses = []
        self.attrs = []
        self.events = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def set_status(self, status):
        self.statuses.append(status)

    def set_attribute(self, key, value):
        self.attrs.append((key, value))

    def add_event(self, name, attributes=None):
        self.events.append((name, attributes or {}))


class _FakeTracer:
    def __init__(self):
        self.calls = []
        self.spans = []

    def start_as_current_span(self, name, **kwargs):
        self.calls.append((name, kwargs.get("attributes", {})))
        span = _FakeSpan()
        self.spans.append(span)
        return span


def _monitor(monkeypatch, glue_response, pagerduty=None, slack=None):
    fake_tracer = _FakeTracer()
    fake_meter = _FakeMeter()
    fake_glue = MagicMock()
    fake_glue.get_job_runs.return_value = {"JobRuns": [glue_response]}

    monkeypatch.setattr(gm, "_setup_glue_otel_provider", lambda: None)
    monkeypatch.setattr(gm.trace, "get_tracer", lambda *_: fake_tracer)
    monkeypatch.setattr(gm.metrics, "get_meter", lambda *_: fake_meter)

    monitor = gm.GlueJobMonitor(
        job_names=["s3-to-redshift-etl"],
        glue_client=fake_glue,
        pagerduty_client=pagerduty,
        slack_client=slack,
    )
    return monitor, fake_glue, fake_tracer, fake_meter


def test_metric_names_match_contract(monkeypatch):
    monitor, _, _, fake_meter = _monitor(
        monkeypatch,
        glue_response={"Id": "jr_1", "JobRunState": "RUNNING"},
    )
    del monitor
    assert {name for _, name in fake_meter.created} == {
        "dataobs.glue.driver.memory.heap.used_percentage",
        "dataobs.glue.driver.disk.used_percentage",
        "dataobs.glue.driver.system.cpuSystemLoad",
        "dataobs.glue.driver.workerUtilization",
        "dataobs.glue.driver.skewness.job",
        "dataobs.glue.job.elapsed_time_ms",
        "dataobs.glue.job.failed_tasks",
        "dataobs.glue.job.failure_count",
    }


async def test_poll_once_deduplicates_and_uses_maxresults_10(monkeypatch):
    run = {"Id": "jr_abc123", "JobRunState": "RUNNING"}
    monitor, fake_glue, fake_tracer, _ = _monitor(monkeypatch, glue_response=run)

    first = await monitor.poll_once()
    second = await monitor.poll_once()

    assert first == ["jr_abc123"]
    assert second == []
    assert fake_glue.get_job_runs.call_args.kwargs["MaxResults"] == 10
    assert fake_tracer.calls[0][1]["event.dataset"] == "aws.glue"
    assert fake_tracer.calls[0][1]["event.provider"] == "glue.amazonaws.com"


def test_failed_run_sets_error_and_routes_to_pagerduty(monkeypatch):
    pagerduty = MagicMock()
    slack = MagicMock()
    run = {
        "Id": "jr_fail_1",
        "JobRunState": "FAILED",
        "GlueVersion": "4.0",
        "WorkerType": "G.1X",
        "NumberOfWorkers": 5,
        "JobCommand": {"Name": "glueetl"},
        "ExecutionTime": 30,
        "ErrorMessage": "Executor lost due to Java heap space",
        "glue.driver.aggregate.numFailedTasks": 3,
    }
    monitor, _, fake_tracer, fake_meter = _monitor(
        monkeypatch,
        glue_response=run,
        pagerduty=pagerduty,
        slack=slack,
    )

    monitor._emit_job_run("s3-to-redshift-etl", run)

    span_attrs = fake_tracer.calls[0][1]
    assert span_attrs["aws.glue.job.name"] == "s3-to-redshift-etl"
    assert span_attrs["aws.glue.job.run_id"] == "jr_fail_1"
    assert span_attrs["aws.glue.job.type"] == "glueetl"
    assert span_attrs["aws.glue.job.run_state"] == "FAILED"
    assert span_attrs["aws.glue.error_category"] == "OUT_OF_MEMORY_ERROR"

    span = fake_tracer.spans[0]
    assert any(key == "error.code" and value == "OUT_OF_MEMORY_ERROR" for key, value in span.attrs)
    assert span.statuses

    failure_counter = fake_meter.by_name["dataobs.glue.job.failure_count"]
    assert any(call[0] == "add" and call[1] == 1 for call in failure_counter.calls)
    pagerduty.trigger.assert_called_once()
    slack.send.assert_not_called()


def test_failed_non_critical_category_routes_to_slack(monkeypatch):
    pagerduty = MagicMock()
    slack = MagicMock()
    run = {
        "Id": "jr_fail_2",
        "JobRunState": "FAILED",
        "JobCommand": {"Name": "pythonshell"},
        "ErrorMessage": "Syntax error at line 27",
    }
    monitor, _, _, _ = _monitor(
        monkeypatch,
        glue_response=run,
        pagerduty=pagerduty,
        slack=slack,
    )

    monitor._emit_job_run("s3-to-redshift-etl", run)
    slack.send.assert_called_once()
    pagerduty.trigger.assert_not_called()
