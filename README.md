# DataObs

## Status

DataObs is under active development. **This repository is not a production release.** Capability state, validation, and release readiness are recorded separately in the [authoritative ledger](docs/product/capability-ledger.yaml); generated state counts are in the [ledger view](docs/product/capability-ledger.md).

## What DataObs is

DataObs is an Elasticsearch-native data-observability system. Elasticsearch and Kibana are the authoritative storage and analysis plane. OpenTelemetry and OpenLineage are ingestion standards. Elastic Agent/Fleet/EDOT and DataObs Scanner are collection mechanisms. The DataObs Console is the opinionated operational UI.

## Canonical six-pillar model

The canonical pillars are **Platform**, **Data Pipeline**, **Data**, **FinOps and Cost**, **Business**, and **AI and Agent**. Cross-cutting Streams, Incident Response, Console, Integrations, and Security domains are represented in the ledger. Future pillars remain `not_started` unless evidence says otherwise.

## Current capability snapshot

See the generated [feature matrix](docs/product/feature-matrix.md) for current state counts and capability-level surfaces, evidence, blockers, and gates. Counts are generated from the machine-readable ledger rather than maintained here.

## Architecture

The [architecture overview](docs/architecture/overview.md) and [six-pillar model](docs/architecture/six-pillar-product-model.md) describe intent. The ledger governs implementation claims when architecture documents describe aspirations.

## Quick start

The local POC instructions are in [docs/poc-setup.md](docs/poc-setup.md). A Compose definition proves configuration exists; it does not by itself prove a real-stack workflow.

## Validated evidence

No capability is currently classified `validated`. Local test results must not be represented as hosted CI. The generated [evidence index](docs/product/evidence-index.md) records definitions, execution status, versions, known runs, and limitations.

## Functional but unvalidated capabilities

Migration mechanics, PostgreSQL scanning, Kafka observation/inventory, incident lifecycle, and bounded incident replay have executable principal workflows but lack all retained evidence required for validation. Consult the ledger for precise scope.

## Known blockers

Hosted run references for the PR #106 head were not available during this audit. Unified Elasticsearch/Kibana 9.4.2, PostgreSQL, Kafka, OpenLineage, browser/accessibility, security, scale, upgrade, backup/restore, IAM, HA, and release evidence remains incomplete or absent.

## Console

A React Console exists with Command Center, Assets, Pathways, Streams, and incident-detail routes. Routes are not equivalent to usable browser-tested workflows. Jobs, Monitoring, Data Products, Automation, and Approvals are absent or planned surfaces; accessibility and browser certification remain blockers.

## APIs

The checked-in [OpenAPI document](openapi.json) is the API contract used by the ledger validator. A planned API is explicitly prefixed `planned:` in the ledger.

## Elasticsearch storage and migrations

Forward migrations `0001`–`0012` define product resources and are checksum-guarded. Declared resources and local migration tests do not prove a hosted rolling upgrade. See the [migration architecture](docs/architecture/elasticsearch-storage-and-migrations.md).

## Integrations

Elasticsearch/Kibana remain authoritative. OpenTelemetry/OpenLineage are standards, not claims of universal connector completeness. OpenSearch, Grafana, Alloy, AMP, and AMG material is optional export/interoperability or legacy POC guidance, never an equal authoritative plane. Cloud and Snowflake providers are not started.

## Deployment

Compose, Kubernetes manifests, a Helm foundation, and limited Terraform modules exist. They do not constitute a complete supported release package.

## Development and CI

The blocking `documentation-truth-gate` validates and renders the ledger, rejects generated drift and stale claims, checks links, and runs documentation tests. Hosted validation requires a retained CI run and artifacts.

## Roadmap

The evidence-gated [roadmap](docs/product/roadmap-v1.md) prioritizes truth, unified certification, core completion, incident workbench, enterprise hardening, then differentiating pillars. It contains no delivery dates.

## Non-goals

This documentation milestone adds no product capability, connector, IAM, backup/restore, or UI completion. Autonomous remediation is not enabled; actions require explicit safety and approval controls.

## Unified product certification

The version-pinned certification harness and its honest evidence policy are documented in [certification/README.md](certification/README.md). Start with `./scripts/certification/compose.sh config`; the environment validates existing surfaces and does not claim whole-product production readiness.
