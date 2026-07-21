# Certification performance and resource budget

This is a certification-scale budget, **not production load testing**. The target hosted runner is `ubuntu-latest` (4 vCPU/16 GiB at time of documentation; verify on each run). Stack readiness is bounded at 300 seconds, backend at 45 minutes, browser at 30 minutes, and security at 30 minutes. Elasticsearch and Kibana each have a 1 GiB container limit; API/PostgreSQL 512 MiB; Console/OTel 256 MiB. Artifacts are limited to 100 MiB each and retained for 14 days on PRs.

The deterministic dataset has two tenants, three environments, one overlapping PostgreSQL table, one three-partition topic, two consumer groups, and bounded lineage/security fixtures. API p95, actual timings, peak memory, and hosted runner identity remain **pending hosted execution** and must be injected into `timing-resource-report.json`; no performance pass is claimed locally.
