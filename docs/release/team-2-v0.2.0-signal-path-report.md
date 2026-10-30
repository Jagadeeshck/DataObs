# Team 2 v0.2.0 End-to-End Signal-Path Report

**Release:** v0.2.0  
**Owner:** Team 2 with Team 3 incident boundary and Team 5 Console dependency  
**Sprint 4 branch:** `codex/sprint4-team2-e2e-proof`  
**Starting main:** `c3d3dfe63b2d8227612dc867988db268c8b7424f`

## Required production path

```
Quality check
  -> OpenTelemetry SDK
  -> OTLP Collector
  -> Elasticsearch
  -> persisted Quality result
  -> canonical Finding
  -> Team 3 incident correlation
  -> deduplicated Incident
  -> notification delivery outcomes
  -> authenticated API retrieval
```

The canonical executable backend contract remains `tests/integration/test_quality_signal_path.py`. Sprint 4 does not replace the Quality runner, OTel path, Finding model, incident engine or delivery implementation.

## Starting-main state

Full CI run `41120485742` did not execute the integration-tests job because shared prerequisite jobs failed. That run is therefore **not** signal-path evidence.

The current shared certification stack also has a Team 0 wiring defect in several focused certification jobs: Elasticsearch is exposed on `127.0.0.1:19200`, while an unscoped migration CLI invocation attempts `localhost:9200`. Team 2 does not rewrite shared release infrastructure to hide that issue.

Quality Monitoring run `41120485805` and Job/Run run `41120485697` are independently verified passes on the starting main SHA, but those focused workflows do not substitute for the end-to-end signal path.

## Sprint 4 exact-SHA producer

`.github/workflows/team-2-sprint4-e2e-proof.yml` runs the existing production-representative integration stack with:

- Elasticsearch 9.4.2;
- the repository API image;
- the repository OTel Collector test configuration;
- the repository mock webhook for delivery outcomes.

Before the signal path, it executes the real Data Product migration regression and retains:

- skip-free Data Product migration JUnit;
- migration status before repeated apply;
- repeated apply output;
- migration status after repeated apply;
- explicit reliability/Data Product mapping types.

It then executes with `RUN_INTEGRATION_TESTS=1`:

- `tests/integration/test_quality_signal_path.py`
- `tests/integration/test_api_e2e.py`
- `tests/integration/test_alert_delivery.py`
- `tests/integration/test_otel_pipeline.py`

The retained artifact is exactly `e2e-signal-path`.

## Required executed scenarios

The signal-path test must prove all of the following in the same real-stack execution:

- a failing nullness check produces a persisted Quality result;
- the Quality execution exports a real OTLP trace through the Collector;
- trace evidence arrives in Elasticsearch with execution and trace correlation;
- a canonical Finding is created;
- Team 3 creates a correlated Incident;
- Slack, PagerDuty and ServiceNow outcomes are captured without credential leakage;
- replay of the same failure deduplicates to the same Incident and increments occurrence count without duplicate notification delivery;
- a different tenant receives a different Incident;
- tenant A cannot retrieve tenant B's Quality result or Finding;
- a successful Quality check produces no Finding and no notification;
- partial notification failure is represented as partial delivery rather than false success.

## Independent verification contract

The independent verifier rejects the artifact unless:

- producer SHA is exactly the final branch head;
- Elasticsearch version is exactly 9.4.2;
- both retained JUnit files contain executed tests;
- failures, errors and **skips are all zero**;
- all required scenarios are present;
- OTel execution/trace IDs match the signal summary;
- incident replay resolves to the same incident;
- notification replay count is zero;
- tenant/environment scope is the expected production scope;
- partial delivery outcomes match the executed test;
- credentials are explicitly marked redaction-safe;
- migration state is unchanged after repeated apply;
- applied migration checksum evidence is complete;
- required mapping types match their canonical writer contracts.

## Sprint 4 result

**Status: PENDING final-head hosted execution.**

Populate only after the final Sprint 4 PR head completes:

- Commit SHA: pending
- Workflow run: pending
- Producer job: pending
- Independent verifier: pending
- Elasticsearch version: must be 9.4.2
- `e2e-signal-path` artifact: pending
- Data Product migration proof: pending
- OTel correlation: pending
- Finding → Incident correlation: pending
- Incident deduplication: pending
- Delivery outcomes: pending
- Tenant isolation: pending
- Skip-free JUnit: pending

Until these fields are backed by retained hosted output for the exact final SHA, Team 2 remains **NO_GO** for the first-release E2E certification row.
