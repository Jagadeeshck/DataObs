# Product certification version matrix

Audited 2026-07-21 against Compose files, Dockerfiles, lockfiles, and CI. Image tags are exact; release hardening should additionally pin image digests. Elastic security is disabled **only** on isolated certification networks. A secured deployment has not been certified, so production readiness remains blocked.

| Component | Image/package | Exact version | Compatibility reason | License note | Evidence |
|---|---|---:|---|---|---|
| Elasticsearch | `docker.elastic.co/elasticsearch/elasticsearch` | 9.4.2 | Required server target | Elastic License 2.0 | certification Compose |
| Kibana | `docker.elastic.co/kibana/kibana` | 9.4.2 | Must match Elasticsearch | Elastic License 2.0 | certification Compose |
| PostgreSQL | `postgres` | 16.9-alpine | Existing 16.x vertical slice | PostgreSQL | certification Compose |
| Kafka KRaft | `bitnami/kafka` | 3.9.0 | Existing real-stack 3.9 line | Apache-2.0 components; image terms apply | certification Compose |
| Kafka Connect | `confluentinc/cp-kafka-connect` | 7.9.0 | Compatible Confluent platform family | Confluent Community License/image terms | certification Compose |
| Schema Registry | `confluentinc/cp-schema-registry` | 7.9.0 | Matches Connect platform family | Confluent Community License/image terms | certification Compose |
| OTel Collector Contrib | `otel/opentelemetry-collector-contrib` | 0.139.0 | Existing PostgreSQL demo pin | Apache-2.0 | certification Compose |
| Python | `python` | 3.11-slim | Production Dockerfiles and CI | PSF | `Dockerfile.api` |
| Node.js | `node` | 24.15.0-alpine | Console production image | MIT | Console Dockerfile |
| pnpm | package manager | 10.28.1 | Console lockfile manager | MIT | Console package.json |
| Playwright browsers | `mcr.microsoft.com/playwright` | v1.58.2-noble | Matches `@playwright/test` | Apache-2.0; browser terms vary | certification Compose |
| Trivy | `aquasecurity/trivy-action` | 0.35.0 | Current repository CI pin | Apache-2.0 | CI |
| Terraform | HashiCorp setup action | 1.13.3 | Certification tooling pin | BUSL-1.1 | CI setup input |
| Helm | Azure setup action | 3.18.4 | Certification tooling pin | Apache-2.0 | CI setup input |

Kafka plaintext and disabled Elastic security are narrow CI limitations, not deployment guidance. Clients must be re-audited when a server pin changes.
