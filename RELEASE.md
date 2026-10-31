# DataObs v1.0.0 — First Release

**Elastic Stack:** 9.5.5  
**Python client:** elasticsearch[async]==9.5.0  
**Console:** 1.0.0  

---

## Local Docker test (MVP stack — quickest path)

The MVP stack is the recommended way to test the first release locally.
It runs Elasticsearch, the DataObs API (with migration bootstrap + demo seed),
and the Console UI — nothing else required.

### 1. Prerequisites

- Docker Desktop ≥ 4.x with at least **8 GB** of RAM allocated
- Ports 8080 and 3000 free

### 2. Create `.env.mvp`

```sh
cp .env.mvp.example .env.mvp
```

Edit `.env.mvp` and set real values:

```
ELASTIC_PASSWORD=<choose-a-password-min-6-chars>
DATAOBS_API_TOKEN=<choose-an-api-token>
ELASTICSEARCH_VERSION=9.5.5
DATAOBS_VERSION=1.0.0
```

### 3. Start the stack

```sh
docker compose --env-file .env.mvp -f docker-compose.mvp.yml up --build
```

First run pulls Elasticsearch 9.5.5 (~1 GB) and builds the API and Console
images, so allow 5–10 minutes. Subsequent starts are much faster.

Services come up in order:

1. **Elasticsearch 9.5.5** — waits for `yellow` health
2. **migrations** — applies all 23 immutable index migrations then exits
3. **demo-seed** — loads demo fixtures then exits
4. **API** — starts on `http://localhost:8080`
5. **Console** — starts on `http://localhost:3000`

### 4. Verify

```sh
# API health
curl http://localhost:8080/health

# Console (opens in browser)
open http://localhost:3000
```

The Console proxies `/api` to the API, so no CORS config is needed.

### 5. Stop and clean up

```sh
# Stop (keeps Elasticsearch data volume)
docker compose --env-file .env.mvp -f docker-compose.mvp.yml down

# Stop and wipe data (full clean)
docker compose --env-file .env.mvp -f docker-compose.mvp.yml down -v
```

---

## Full local stack (Elasticsearch + Kibana + APM + OTel)

```sh
cp .env.example .env
# Edit .env: set ELASTIC_PASSWORD and KIBANA_PASSWORD
docker compose up -d
```

Services: Elasticsearch, Kibana, APM Server, OTel Collector, DataObs Quality
Engine, DataObs API. All on `docker-compose.yml`.

---

## POC stack (Elastic Agent + Fleet)

```sh
cp .env.poc .env.poc.local
# Edit ELASTIC_PASSWORD and KIBANA_PASSWORD
docker compose --env-file .env.poc.local -f docker-compose.poc.yml up -d
```

---

## Version summary

| Component | Version |
|---|---|
| Elasticsearch | 9.5.5 |
| Kibana | 9.5.5 |
| APM Server | 9.5.5 |
| Elastic Agent / Fleet | 9.5.5 |
| elasticsearch-py client | 9.5.0 |
| DataObs API | 1.0.0 |
| DataObs Console | 1.0.0 |
| Python base image | 3.11-slim |
| Node.js build image | 24.15.0-alpine |
| nginx runtime | nginxinc/nginx-unprivileged:1.29.4-alpine |
| OTel Collector | 0.139.0 (certification) / 0.126.0 (full stack) |
