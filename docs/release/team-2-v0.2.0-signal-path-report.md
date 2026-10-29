# Team 2 v0.2.0 End-to-End Signal-Path Report

**Release:** v0.2.0  
**Owner:** Team 2 with Team 3 incident boundary and Team 5 Console investigation dependency  
**Certification branch:** `codex/sprint3-team2-data-certification`

## Required production path

```
Quality check
  -> OpenTelemetry SDK
  -> OTLP Collector
  -> Elasticsearch trace/evidence
  -> persisted Quality result
  -> canonical Finding
  -> Team 3 incident correlation
  -> deduplicated Incident
  -> notification outcomes
  -> authenticated API retrieval
  -> Console investigation
```

The canonical executable backend contract is `tests/integration/test_quality_signal_path.py`, executed by the CI integration job with `RUN_INTEGRATION_TESTS=1`.

## What the executable scenario proves

The scenario must execute against the real integration stack, not fixtures alone. It proves:

- a failing nullness check produces a persisted Quality result;
- the Quality execution exports a real OTLP trace through the Collector;
- the trace arrives in Elasticsearch and preserves execution/trace correlation;
- a canonical Finding is created;
- Team 3 creates a correlated Incident;
- Slack, PagerDuty and ServiceNow notification outcomes are captured by the integration webhook;
- credentials are absent from retained notification evidence;
- replay of the same failure deduplicates to the same Incident and increments occurrence count without duplicate notification delivery;
- a second tenant receives a different Incident;
- tenant A cannot retrieve tenant B's Quality result or Finding;
- a successful Quality check produces no Finding and no notification;
- partial notification failure is represented as partial delivery, not false success.

## Required retained artifact

The CI job must retain `artifacts/e2e-signal-path` for the exact final SHA, including:

- `signal-path-summary.json`
- `otel-correlation.json`
- `alert-delivery-summary.json`
- JUnit from the integration run

The summary must identify the exact commit, Elasticsearch version, execution ID, trace ID, tenant, environment, scenarios and deduplication result.

## Previous state

The earlier Team 2 release closure defined this scenario but did not have final release evidence that could be promoted for Sprint 3. A skipped integration test, a fixture-only browser journey or an artifact generated after an upstream failure is not acceptable evidence.

## Sprint 3 result

**Status: PENDING exact-SHA hosted execution.**

Populate after the PR-head CI integration job completes:

- Commit SHA: pending
- CI run: pending
- Integration job: pending
- Elasticsearch version: must be 9.4.2
- Signal-path artifact: pending
- Finding → Incident correlation: pending
- Incident deduplication: pending
- Notification outcomes: pending
- Tenant isolation: pending
- Independent/exact-SHA evidence check: pending
- Console investigation journey: pending

Until these fields are backed by retained hosted output, this report is not a release certification.
