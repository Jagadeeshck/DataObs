# SkillRadar Elastic-native observability integration

This guide connects the local **SkillRadar** product stack to the local **DataObs** observability stack so SkillRadar can be used as a live DataObs showcase.

The goal is to capture application performance, traces, logs, container metrics, infrastructure metrics, Elasticsearch indexing/search health, and SkillRadar business events in Elastic/Kibana.

## Why this integration exists

SkillRadar is an AI career-intelligence product with realistic application flows:

- Resume upload and parsing
- Skill extraction
- Job classification
- Recommendation scoring
- Elasticsearch indexing
- Frontend user journeys
- Business KPI events

That makes it a strong demo workload for DataObs. Instead of using a synthetic demo only, DataObs can show real full-stack observability for a real product.

## Local port ownership

When both projects run locally, keep their ports separated.

| Component | Project | Host URL | Purpose |
|---|---|---|---|
| DataObs Elasticsearch | DataObs | `http://localhost:9200` | Observability backend |
| DataObs Kibana | DataObs | `http://localhost:5601` | Dashboards, APM, logs, metrics |
| DataObs API | DataObs | `http://localhost:8080` | DataObs API |
| SkillRadar API | SkillRadar | `http://localhost:8000` | Product API |
| SkillRadar Web | SkillRadar | `http://localhost:3000` | Product UI |
| SkillRadar Elasticsearch | SkillRadar | `http://localhost:9201` | Product search index, `jobs-v1` |

Recommended split:

- **DataObs Elasticsearch on 9200** receives observability data.
- **SkillRadar Elasticsearch on 9201** stores product search data.
- SkillRadar APM, logs, and business telemetry should go to DataObs, not to the SkillRadar product Elasticsearch.

## Target architecture

```text
SkillRadar Web / Browser
  └─ frontend telemetry events
        └─ SkillRadar API /telemetry/events

SkillRadar API
  ├─ Elastic APM Python agent
  ├─ ECS JSON access logs
  ├─ ECS JSON business logs
  ├─ resume analysis spans
  ├─ job classification spans
  ├─ recommendation spans
  └─ Elasticsearch indexing spans

Elastic Agent / Fleet-style collector
  ├─ Docker container logs
  ├─ Docker metrics
  ├─ System metrics
  ├─ SkillRadar API JSON logs
  ├─ PostgreSQL metrics/logs
  ├─ Redis metrics/logs
  └─ SkillRadar Elasticsearch metrics/logs

DataObs Elasticsearch + Kibana
  ├─ APM traces and service maps
  ├─ logs-skillradar.api-*
  ├─ logs-skillradar.business-*
  ├─ metrics-docker-*
  ├─ metrics-system-*
  ├─ metrics-postgresql-*
  ├─ metrics-redis-*
  └─ metrics-elasticsearch-*
```

## Start DataObs first

From the `DataObs` repository:

```bash
cp .env.example .env
# Edit .env and set at least ELASTIC_PASSWORD and KIBANA_PASSWORD

docker compose up -d
```

Verify:

```bash
curl -u elastic:<ELASTIC_PASSWORD> http://localhost:9200/_cluster/health?pretty
open http://localhost:5601
curl http://localhost:8080/health
```

DataObs already runs Elasticsearch 9.x and Kibana on the default local ports. The root compose uses `elasticsearch:${ELK_VERSION:-9.4.2}` and exposes Elasticsearch on `9200:9200`; Kibana is exposed on `5601:5601`.

## Configure SkillRadar APM to send traces to DataObs

SkillRadar should keep its own product Elasticsearch URL as:

```env
ELASTICSEARCH_URL=http://elasticsearch:9201
```

That is for SkillRadar product search only.

For APM, configure SkillRadar to send traces to the DataObs APM integration endpoint.

In SkillRadar `.env`:

```env
ELASTIC_APM_ENABLED=true
ELASTIC_APM_SERVICE_NAME=skillradar-api
ELASTIC_APM_SERVER_URL=http://host.docker.internal:8200
ELASTIC_APM_SECRET_TOKEN=
ELASTIC_APM_API_KEY=
ELASTIC_APM_ENVIRONMENT=local-demo
ELASTIC_APM_SERVICE_VERSION=0.1.0
ELASTIC_APM_TRANSACTION_SAMPLE_RATE=1.0
ELASTIC_APM_CAPTURE_BODY=off
ELASTIC_APM_CAPTURE_HEADERS=true
```

Notes:

- Use `host.docker.internal` from SkillRadar containers to reach services exposed by the DataObs Docker stack on the host.
- If your DataObs stack exposes APM through Fleet/Elastic Agent instead of a standalone APM Server container, use the APM endpoint shown in Kibana Fleet.
- Keep `ELASTIC_APM_CAPTURE_BODY=off`; resume text must not be captured in traces.
- Prefer API key or secret token for production-like demos.

## APM endpoint options

### Option A — Elastic APM integration via Fleet

Use Kibana:

```text
Kibana → Management → Fleet → Agent policies → Add integration → APM
```

Create or use policy:

```text
dataobs-skillradar-observability-pack
```

Then use the APM server URL shown by the APM integration.

### Option B — local APM Server service

If you add a standalone `apm-server` service to DataObs later, expose it on `8200` and point SkillRadar to:

```env
ELASTIC_APM_SERVER_URL=http://host.docker.internal:8200
```

Do not enable request-body capture for resume workflows.

## Capture SkillRadar ECS JSON logs

SkillRadar emits ECS-style JSON logs for two key datasets:

| Dataset | Meaning |
|---|---|
| `skillradar.api` | One API access event per request |
| `skillradar.business` | Product telemetry: jobs, resumes, recommendations, indexing, frontend events |

Recommended DataObs / Elastic Agent collection methods:

1. Docker integration for all SkillRadar container logs.
2. Custom logs integration filtered to SkillRadar API container logs.
3. Preserve JSON fields during ingestion.
4. Route by `event.dataset` where possible.

Target data streams:

```text
logs-skillradar.api-local
logs-skillradar.business-local
```

Example important fields:

```text
service.name=skillradar-api
event.dataset=skillradar.api
event.dataset=skillradar.business
event.action=resume.analysed
event.action=recommendations.generated
event.action=elasticsearch.index.success
skillradar.skills_count
skillradar.resume_seniority
skillradar.target_roles
skillradar.recommendations_count
skillradar.match_score_avg
labels.request_id
trace.id
transaction.id
```

Sensitive fields must not be indexed:

```text
resume_text
raw_resume_text
extracted_text
file_contents
secret
token
password
```

## Elastic Agent policy for SkillRadar

Recommended policy name:

```text
dataobs-skillradar-observability-pack
```

Recommended integrations:

| Integration | Captures |
|---|---|
| System | Host CPU, memory, filesystem, network |
| Docker | Container CPU/memory/network/logs |
| PostgreSQL | SkillRadar PostgreSQL metrics/logs |
| Redis | SkillRadar Redis metrics/logs |
| Elasticsearch | SkillRadar product Elasticsearch metrics/logs on port 9201 |
| APM | SkillRadar API traces, transactions, errors |
| Custom logs | SkillRadar ECS JSON business/API logs |
| Synthetics later | UI/API availability checks |

For local Docker, the Elastic Agent needs Docker socket and container log mounts:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
  - /var/lib/docker/containers:/var/lib/docker/containers:ro
  - /sys/fs/cgroup:/hostfs/sys/fs/cgroup:ro
  - /proc:/hostfs/proc:ro
  - /:/hostfs:ro
```

## Recommended Kibana data views

Create data views:

```text
traces-apm*
logs-apm*
metrics-apm*
logs-skillradar.api-*
logs-skillradar.business-*
metrics-docker-*
metrics-system-*
metrics-postgresql-*
metrics-redis-*
metrics-elasticsearch-*
```

## Dashboards to build

### 1. SkillRadar executive overview

Panels:

- Active jobs
- Jobs classified today
- Resumes analysed today
- Recommendations generated today
- Average recommendation match score
- API p95 latency
- API error rate
- Elasticsearch indexing failures
- Top missing skills

### 2. SkillRadar API performance

Panels:

- Transactions by endpoint
- p50 / p95 / p99 latency by endpoint
- Error rate by endpoint
- Slowest traces
- Dependency latency: PostgreSQL, Redis, Elasticsearch
- Requests by `labels.request_id`

### 3. Resume intelligence

Panels:

- Resume uploads by file type
- Resume analysis duration
- Extracted skills count distribution
- Seniority distribution
- Target role family distribution
- Resume analysis failures

### 4. Recommendation engine

Panels:

- Recommendation requests over time
- Average match score
- Recommendations returned per request
- Top missing skills
- Zero-match recommendation events
- Slow recommendation traces

### 5. Job classification

Panels:

- Jobs classified over time
- Role family distribution
- Top extracted skills
- SkillRadar score distribution
- Search/Elasticsearch/OpenSearch role count
- MLOps/AI Platform role count

### 6. Search platform

Panels:

- SkillRadar `jobs-v1` document count
- Indexing success/failure events
- Elasticsearch indexing latency
- Search latency
- SkillRadar Elasticsearch JVM/CPU/disk
- Cluster health

### 7. Infrastructure health

Panels:

- SkillRadar API container CPU/memory
- SkillRadar web container CPU/memory
- PostgreSQL CPU/memory/connections
- Redis memory/ops
- SkillRadar Elasticsearch heap/disk

## Screenshot plan for DataObs website

Capture these screenshots after running a full SkillRadar demo:

1. Kibana APM service map showing `skillradar-api`.
2. A trace waterfall for `/resume/analyse`.
3. A trace waterfall for `/recommendations/jobs`.
4. API latency chart by endpoint.
5. Error overview.
6. Docker/container metrics for SkillRadar services.
7. Business KPI dashboard showing resumes analysed, jobs classified, recommendations generated.
8. Skill demand dashboard showing top skills and role families.
9. Elasticsearch indexing/search dashboard for `jobs-v1`.

## Demo runbook

Start DataObs:

```bash
cd DataObs
docker compose up -d
open http://localhost:5601
```

Start SkillRadar:

```bash
cd ../skillradar
make demo
```

Generate product activity:

```text
1. Open http://localhost:3000/dashboard
2. Open http://localhost:3000/jobs
3. Upload a resume at http://localhost:3000/resume
4. Generate recommendations
5. Click into recommended job details
6. Search/filter jobs
```

Validate local SkillRadar product data:

```bash
curl http://localhost:8000/dashboard/stats
curl http://localhost:9201/jobs-v1/_search?pretty
```

Validate DataObs observability data in Kibana:

```text
Discover → traces-apm*
Discover → logs-skillradar.business-*
Discover → logs-skillradar.api-*
Observability → APM → Services → skillradar-api
```

## Troubleshooting

### SkillRadar product works but no APM data appears

Check:

```bash
docker compose logs api
```

Verify SkillRadar `.env`:

```env
ELASTIC_APM_ENABLED=true
ELASTIC_APM_SERVER_URL=http://host.docker.internal:8200
ELASTIC_APM_SERVICE_NAME=skillradar-api
```

Check whether DataObs exposes an APM endpoint and whether token/API key is required.

### SkillRadar cannot reach DataObs from Docker

From a SkillRadar container:

```bash
docker compose exec api python - <<'PY'
from urllib.request import urlopen
print(urlopen('http://host.docker.internal:9200', timeout=5).status)
PY
```

For Elasticsearch with security enabled, use credentials:

```bash
curl -u elastic:<ELASTIC_PASSWORD> http://localhost:9200
```

### SkillRadar recommendations work but business logs do not appear

Check local API logs first:

```bash
cd skillradar
make logs-api
```

Look for:

```text
event.dataset=skillradar.business
event.action=resume.analysed
event.action=recommendations.generated
```

Then confirm Elastic Agent custom logs integration is collecting SkillRadar API container logs and preserving JSON keys.

### Port conflicts

Use this split:

```text
DataObs Elasticsearch: localhost:9200
SkillRadar Elasticsearch: localhost:9201
DataObs Kibana: localhost:5601
SkillRadar API: localhost:8000
SkillRadar Web: localhost:3000
```

If `3000` conflicts with Grafana profile, do not run the DataObs Grafana profile while running SkillRadar web, or remap one of the ports.
