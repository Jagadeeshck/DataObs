# Certification Compose consolidation audit

| Environment | Classification | Reuse/decision |
|---|---|---|
| `docker-compose.yml` | reused | Production service entry points and OTel conventions. |
| `docker-compose.poc.yml` | legacy_demo | Preserved; no longer a certification authority. |
| `docker-compose.postgres-demo.yml` | wrapped | Scanner, secret-file, and PostgreSQL slice reused. |
| `docker-compose.kafka-observer-real-stack.yml` | wrapped | Three-broker KRaft, Connect, Registry, and observer topology reused with exact Kafka tag. |
| `docker-compose.incident-automation-demo.yml` | legacy_demo | Preserved for focused incident demonstrations. |
| `docker-compose.console-demo.yml` | superseded | Certification browser profile is the retained-evidence path; demo remains for now. |
| `docker-compose.job-run-demo.yml` | legacy_demo | Deterministic contract only; no real provider certification. |
| `tests/integration/docker-compose.test.yml` | reused | Existing API/Elastic integration remains a focused gate. |
| `integrations/grafana-alloy/docker-compose.yml` | optional_integration | Grafana is not an authoritative plane. |

No demo is deleted in this phase. Remove later only after hosted equivalence and reference cleanup are proven.
