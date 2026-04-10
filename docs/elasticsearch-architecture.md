# DataObs — Elasticsearch Two-Tier Architecture

## Overview

DataObs uses a **two-tier Elasticsearch topology** to separate platform concerns (the DataObs product team manages the server side) from tenant concerns (each customer has their own isolated view of their data).

```
╔══════════════════════════════════════════════════════════════════════╗
║  TENANT SIDE (per customer)                                          ║
║                                                                      ║
║  AWS Lambda / EMR / Glue / Athena / RDS / EKS (tenant pipelines)    ║
║         │ OTel SDK (Python/Java/Node)                                ║
║         ▼                                                            ║
║  OTel Collector (tenant) ──── otel-collector-tenant-overlay.yaml    ║
║         │ injects dataobs.tenant_id via resource/tenant processor    ║
║         │ authenticates with per-tenant API key (Secrets Manager)    ║
║         ▼                                                            ║
║  ┌─────────────────────────────────────────────────────────┐        ║
║  │  Tenant OpenSearch Domain (t3.medium, single-AZ)        │        ║
║  │  • Read-only view via CCR replicated indices            │        ║
║  │  • DLS: dataobs.tenant_id == <this tenant>              │        ║
║  │  • Kibana dashboards scoped to tenant                   │        ║
║  └────────────────────────────┬────────────────────────────┘        ║
╚═══════════════════════════════│═════════════════════════════════════╝
                                │ CCR pull replication
                                │ (quality-results, lineage, freshness)
╔═══════════════════════════════▼═════════════════════════════════════╗
║  SERVER SIDE (DataObs platform)                                      ║
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────┐        ║
║  │  DataObs OpenSearch Cluster (server)                    │        ║
║  │  • 3 dedicated master nodes (m6g.large)                 │        ║
║  │  • 3 hot data nodes (r6g.large, 500 GiB gp3 each)       │        ║
║  │  • 2 warm nodes (UltraWarm)                             │        ║
║  │  • KMS encryption at rest, TLS in transit               │        ║
║  │  • Fine-grained access control (FGAC)                   │        ║
║  │  • ILM: hot 7d → warm 30d → cold 90d → delete 365d     │        ║
║  │  • Nightly S3 snapshots (SLM)                           │        ║
║  │  • Ingest pipeline: dataobs-enrich                      │        ║
║  └─────────────────────────────────────────────────────────┘        ║
║         │                                                            ║
║         ▼                                                            ║
║  DataObs API  ◄──  Quality Engine  ◄──  OTel Collector (server)     ║
║  Kibana (platform ops dashboards)                                    ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Data Flow

1. **Tenant pipeline runs** — Lambda/Glue/EMR/EKS emits OTel signals via SDK
2. **Tenant OTel collector** picks up signals, injects `dataobs.tenant_id` via `resource/tenant` processor, authenticates with a per-tenant API key fetched from Secrets Manager
3. **Server cluster ingests** all tenant signals through the `dataobs-enrich` ingest pipeline, which normalises timestamps, extracts AWS ARN components, and defaults missing tenant metadata
4. **Quality Engine** runs checks (freshness, row count, schema, null, lineage) and writes results back to `dataobs-quality-results-*` with `dataobs.tenant_id` set
5. **CCR replication** pulls `dataobs-quality-results-*`, `dataobs-lineage-*`, and `dataobs-freshness-*` from the server cluster to each tenant's read-only cluster automatically as new indices roll over
6. **Tenant Kibana** queries only the tenant cluster, DLS ensures cross-tenant leakage is impossible even if a query reaches the wrong index

## Security Model

| Layer | Mechanism | Effect |
|---|---|---|
| Network | VPC security groups, private subnets | Cluster unreachable from public internet |
| Transport | TLS 1.2+ enforced (`enforce_https = true`) | All data in transit encrypted |
| Storage | KMS at-rest encryption (separate keys per tier) | Data at rest encrypted, keys rotatable |
| Authn | Fine-grained access control (FGAC), API keys | No anonymous access |
| Authz | Per-tenant role + DLS query | Tenant can only see `dataobs.tenant_id == their_id` |
| Isolation | Separate OpenSearch domain per tenant | Noisy-neighbour and blast-radius isolation |

## Tenant Onboarding Runbook

### Prerequisites
- Terraform workspace for the tenant's AWS account
- VPC peering or AWS PrivateLink between tenant VPC and DataObs server VPC
- Tenant `tenant_id` agreed (lowercase alphanumeric, max 28 chars)

### Steps

```bash
# 1. Provision the tenant OpenSearch domain
cd infra/terraform/elasticsearch/tenant
terraform init
terraform apply \
  -var="tenant_id=acme" \
  -var="tenant_vpc_id=vpc-xxxx" \
  -var="tenant_vpc_cidr=10.10.0.0/16" \
  -var="tenant_subnet_id=subnet-xxxx" \
  -var="server_es_sg_id=sg-xxxx" \
  -var="server_es_endpoint=https://search-dataobs-server-xxx.eu-west-1.es.amazonaws.com" \
  -var="tenant_es_master_user=admin" \
  -var="tenant_es_master_password=<from-vault>" \
  -var="tenant_es_api_key=<pre-generated>" \
  -var='tenant_allowed_role_arns=["arn:aws:iam::123456789:role/dataobs-tenant-acme"]'

# 2. Bootstrap the tenant Elasticsearch configuration
export TENANT_ID=acme
export TENANT_ES_ENDPOINT=$(terraform output -raw tenant_endpoint)
export TENANT_ES_USER=admin
export TENANT_ES_PASSWORD=<from-vault>
export SERVER_ES_ENDPOINT=https://search-dataobs-server-xxx.eu-west-1.es.amazonaws.com
export SERVER_ES_USER=admin
export SERVER_ES_PASSWORD=<from-vault>
python config/elasticsearch/tenant/tenant-bootstrap.py

# 3. Deploy tenant OTel collector with overlay
# Merge otel-collector-tenant-overlay.yaml into the base config and deploy
# Set the following env vars on the collector container:
#   DATAOBS_SERVER_ENDPOINT, DATAOBS_TENANT_ID, DATAOBS_TENANT_API_KEY
# The API key can be retrieved from Secrets Manager:
aws secretsmanager get-secret-value \
  --secret-id dataobs/tenants/acme/otel-api-key \
  --query SecretString --output text | jq -r .api_key
```

## Sizing Guide

| Component | Dev/Test | Production |
|---|---|---|
| Server hot nodes | 3 × `t3.medium.search` 100 GiB | 3 × `r6g.large.search` 500 GiB |
| Server master nodes | 3 × `t3.medium.search` | 3 × `m6g.large.search` |
| Server warm nodes | 2 × `ultrawarm1.medium.search` | 2 × `ultrawarm1.large.search` |
| Tenant domain | 1 × `t3.small.search` 20 GiB | 1 × `t3.medium.search` 100 GiB |
| Snapshot retention | 7 days | 30 days (5 min, 30 max) |
