# =============================================================================
# DataObs — AWS Backend: Outputs
# =============================================================================

# ── AMP ───────────────────────────────────────────────────────────────────────
output "amp_workspace_id" {
  description = "AMP workspace ID."
  value       = module.amp.workspace_id
}

output "amp_workspace_arn" {
  description = "AMP workspace ARN."
  value       = module.amp.workspace_arn
}

output "amp_remote_write_url" {
  description = "AMP Remote Write URL. Set as AMP_REMOTE_WRITE_URL env var on the OTel Collector."
  value       = module.amp.remote_write_url
}

output "amp_query_url" {
  description = "AMP query URL for Grafana data source."
  value       = module.amp.query_url
}

# ── OSIS ──────────────────────────────────────────────────────────────────────
output "osis_traces_endpoint" {
  description = "OSIS traces ingestion endpoint. Set as OSIS_PIPELINE_ENDPOINT on the OTel Collector for traces."
  value       = module.osis.traces_ingest_endpoint
}

output "osis_logs_endpoint" {
  description = "OSIS logs ingestion endpoint."
  value       = module.osis.logs_ingest_endpoint
}

output "osis_metrics_endpoint" {
  description = "OSIS metrics ingestion endpoint."
  value       = module.osis.metrics_ingest_endpoint
}

output "osis_traces_pipeline_arn" {
  description = "OSIS traces pipeline ARN."
  value       = module.osis.traces_pipeline_arn
}

output "osis_logs_pipeline_arn" {
  description = "OSIS logs pipeline ARN."
  value       = module.osis.logs_pipeline_arn
}

output "osis_metrics_pipeline_arn" {
  description = "OSIS metrics pipeline ARN."
  value       = module.osis.metrics_pipeline_arn
}

# ── AMG ───────────────────────────────────────────────────────────────────────
output "amg_workspace_id" {
  description = "AMG workspace ID."
  value       = module.amg.workspace_id
}

output "amg_workspace_url" {
  description = "AMG Grafana URL. Open in a browser to access dashboards."
  value       = module.amg.workspace_url
}

output "amg_grafana_version" {
  description = "Grafana version running on the AMG workspace."
  value       = module.amg.grafana_version
}

output "amg_service_account_token_secret_arn" {
  description = "Secrets Manager ARN holding the Grafana Terraform service account token."
  value       = module.amg.service_account_token_secret_arn
  sensitive   = true
}

# ── IAM ───────────────────────────────────────────────────────────────────────
output "collector_role_arn" {
  description = "OTel Collector IAM role ARN. Attach to EC2 instance profile / ECS task role / EKS IRSA annotation."
  value       = module.iam.collector_role_arn
}

output "collector_instance_profile_arn" {
  description = "EC2 instance profile ARN for the OTel Collector."
  value       = module.iam.collector_instance_profile_arn
}

output "osis_pipeline_role_arn" {
  description = "OSIS pipeline IAM role ARN."
  value       = module.iam.osis_pipeline_role_arn
}

output "amg_role_arn" {
  description = "AMG workspace IAM role ARN."
  value       = module.iam.amg_role_arn
}

# ── Collector environment block (copy into docker-compose .env or ECS task def) ──
output "otel_collector_env" {
  description = "Key/value map of environment variables to set on the OTel Collector for the AWS backend."
  value = {
    DATAOBS_BACKEND        = "aws_grafana"
    AMP_REMOTE_WRITE_URL   = module.amp.remote_write_url
    OSIS_PIPELINE_ENDPOINT = module.osis.traces_ingest_endpoint # primary: traces
    OSIS_LOGS_ENDPOINT     = module.osis.logs_ingest_endpoint
    OSIS_METRICS_ENDPOINT  = module.osis.metrics_ingest_endpoint
    AWS_REGION             = var.aws_region
  }
}
