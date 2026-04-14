# DataObs — AWS Backend Terraform Module

Provisions the full AWS observability backend for DataObs in a single `terraform apply`:

| Resource | Module | What it creates |
|---|---|---|
| **Amazon Managed Prometheus (AMP)** | `modules/amp` | AMP workspace, CloudWatch log group, ingestion error alarm, SSM parameters |
| **Amazon OpenSearch Ingestion (OSIS)** | `modules/osis` | 3 OSIS pipelines (traces / logs / metrics), CloudWatch log groups, SSM parameters |
| **Amazon Managed Grafana (AMG)** | `modules/amg` | AMG workspace, service account + Secrets Manager token, 5 pre-wired data sources |
| **IAM roles** | `modules/iam` | OTel Collector role, OSIS pipeline role, AMG workspace role + all scoped policies |

---

## Architecture

```
OTel Collector (EC2 / ECS / EKS)
    │
    ├── prometheusremotewrite/amp ──► AMP workspace ──────────────────────┐
    │                                                                       │
    ├── otlphttp/opensearch_aws ──► OSIS traces pipeline                  │
    │                                   └── OpenSearch trace-analytics-*   │
    │                                                                       │
    ├── otlphttp/opensearch_aws ──► OSIS logs pipeline                    │
    │                                   └── OpenSearch dataobs-logs-*      │
    │                                                                       │
    └── otlphttp/opensearch_aws ──► OSIS metrics pipeline                 │
                                        ├── OpenSearch dataobs-metrics     │
                                        └── AMP (fan-out) ─────────────────┘
                                                                           │
                                                               Amazon Managed Grafana
                                                               Data sources:
                                                                 ├── AMP (metrics)
                                                                 ├── OpenSearch (traces)
                                                                 ├── OpenSearch (logs)
                                                                 ├── X-Ray
                                                                 └── CloudWatch
```

---

## Prerequisites

1. **Amazon OpenSearch Service domain** — must exist before running this module.
   Use `infra/terraform/elasticsearch/` or provision separately.

2. **AWS IAM Identity Center (SSO)** — required for `amg_permission_type = "SERVICE_MANAGED"`.
   If SSO is not enabled, set `amg_permission_type = "CUSTOMER_MANAGED"`.

3. **Terraform** `>= 1.5.0` and **AWS provider** `>= 5.36` (for OSIS support).

4. **Grafana Terraform provider** `>= 3.0` (used by the AMG module to provision data sources).

---

## Quick Start

```bash
cd infra/terraform/aws-backend

# 1. Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
# edit: aws_region, opensearch_domain_name, etc.

# 2. Initialise providers
terraform init

# 3. Plan
terraform plan -out=tfplan

# 4. Apply (two-phase — see note below)
terraform apply tfplan
```

### Two-phase apply (OSIS ARN tightening)

On the first apply, the OTel Collector IAM policy uses `osis:Ingest` on `*` (all pipelines)
because the OSIS ARNs are not yet known. After the first apply, tighten it:

```bash
# Get the real pipeline ARNs from outputs
terraform output osis_traces_pipeline_arn   # arn:aws:osis:...:pipeline/dataobs-prod-traces
terraform output osis_logs_pipeline_arn
terraform output osis_metrics_pipeline_arn

# Set the variable and re-apply (only the IAM module changes)
terraform apply -var="osis_pipeline_arn_override=arn:aws:osis:us-east-1:123456789012:pipeline/dataobs-prod-traces"
```

---

## Activate the OTel Collector

After `terraform apply`, copy the collector environment block from outputs:

```bash
terraform output -json otel_collector_env
```

Example output:
```json
{
  "AMP_REMOTE_WRITE_URL":   "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-xxx/api/v1/remote_write",
  "AWS_REGION":             "us-east-1",
  "DATAOBS_BACKEND":        "aws_grafana",
  "OSIS_LOGS_ENDPOINT":     "https://dataobs-prod-logs-abc.us-east-1.osis.amazonaws.com",
  "OSIS_METRICS_ENDPOINT":  "https://dataobs-prod-metrics-abc.us-east-1.osis.amazonaws.com",
  "OSIS_PIPELINE_ENDPOINT": "https://dataobs-prod-traces-abc.us-east-1.osis.amazonaws.com"
}
```

Set these on your OTel Collector instances (EC2 user-data, ECS task definition, Helm values).

---

## Module Inputs

### Root module (`aws-backend/`)

| Variable | Type | Default | Description |
|---|---|---|---|
| `aws_region` | string | `us-east-1` | AWS region |
| `name_prefix` | string | `dataobs` | Resource name prefix |
| `environment` | string | `prod` | Environment label (prod/staging/dev) |
| `opensearch_domain_name` | string | — | **Required.** Existing OpenSearch domain name |
| `osis_min_units` | number | `1` | Min OSIS capacity units per pipeline |
| `osis_max_units` | number | `4` | Max OSIS capacity units per pipeline |
| `enable_amp_metrics_fanout` | bool | `true` | Fan metrics from OSIS to AMP |
| `grafana_version` | string | `10.4` | Grafana version on AMG |
| `amg_authentication_providers` | list(string) | `["AWS_SSO"]` | AMG auth providers |
| `amg_permission_type` | string | `SERVICE_MANAGED` | AMG IAM permission mode |
| `eks_oidc_provider_arn` | string | `null` | EKS OIDC ARN for IRSA (optional) |
| `log_retention_days` | number | `90` | CloudWatch log retention |

Full variable descriptions: [`variables.tf`](variables.tf)

### Key Outputs

| Output | Description |
|---|---|
| `amg_workspace_url` | AMG Grafana URL — open in browser |
| `amp_remote_write_url` | AMP Remote Write URL for OTel Collector |
| `osis_traces_endpoint` | OSIS traces ingestion endpoint |
| `osis_logs_endpoint` | OSIS logs ingestion endpoint |
| `osis_metrics_endpoint` | OSIS metrics ingestion endpoint |
| `collector_role_arn` | OTel Collector IAM role ARN |
| `otel_collector_env` | Ready-to-paste env block for the OTel Collector |

---

## Modules

### `modules/iam`

Creates three IAM roles:

| Role | Principal | Key permissions |
|---|---|---|
| `dataobs-otel-collector` | EC2 / ECS / EKS (IRSA) | `aps:RemoteWrite`, `osis:Ingest`, CloudWatch read, X-Ray write, SSM core |
| `dataobs-osis-pipeline` | `osis-pipelines.amazonaws.com` | `es:ESHttp*`, CloudWatch logs write, `aps:RemoteWrite` |
| `dataobs-amg-workspace` | `grafana.amazonaws.com` | AMP query, OpenSearch read, CloudWatch read, X-Ray read, SNS publish |

### `modules/amp`

Creates an AMP workspace with:
- CloudWatch log group (configurable retention)
- CloudWatch alarm on `RemoteWriteInvalidRequests`
- SSM Parameters: `/dataobs/amp/remote-write-url`, `/dataobs/amp/workspace-id`

### `modules/osis`

Creates three OSIS pipelines (traces / logs / metrics):
- Each pipeline has its own CloudWatch log group
- Metrics pipeline optionally fans out to AMP
- SSM Parameters for each ingestion endpoint

### `modules/amg`

Creates an AMG workspace with:
- Service account + Secrets Manager-stored token (for Terraform-managed provisioning)
- 5 pre-wired data sources: AMP (metrics), OpenSearch (traces + logs), X-Ray, CloudWatch
- `DataObs` Grafana folder for dashboard imports
- SSM Parameter: `/dataobs/amg/workspace-url`

---

## State Management

For team use, configure the S3 backend in `main.tf`:

```hcl
backend "s3" {
  bucket         = "your-tfstate-bucket"
  key            = "dataobs/aws-backend/terraform.tfstate"
  region         = "us-east-1"
  dynamodb_table = "terraform-lock"
  encrypt        = true
}
```

---

## Related

- [`infra/terraform/elasticsearch/`](../elasticsearch/) — OpenSearch/Elasticsearch domain
- [`infra/terraform/aws-ec2-otel-agent/`](../aws-ec2-otel-agent/) — SSM-managed OTel agent install
- [`config/otel-collector-config.yaml`](../../../config/otel-collector-config.yaml) — Collector config with AWS backend pipelines
- [`docs/aws-grafana-setup.md`](../../../docs/aws-grafana-setup.md) — Manual setup walkthrough
