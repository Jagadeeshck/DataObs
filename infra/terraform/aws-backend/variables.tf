# =============================================================================
# DataObs — AWS Backend: Input Variables
# =============================================================================

# ── Core ──────────────────────────────────────────────────────────────────────
variable "aws_region" {
  description = "AWS region to deploy into (e.g. 'us-east-1', 'eu-west-2')."
  type        = string
  default     = "us-east-1"
}

variable "name_prefix" {
  description = "Short name prefix for all resource names. Combined with environment: '<prefix>-<env>'."
  type        = string
  default     = "dataobs"
}

variable "environment" {
  description = "Deployment environment label (e.g. 'prod', 'staging', 'dev')."
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["prod", "staging", "dev", "sandbox"], var.environment)
    error_message = "environment must be one of: prod, staging, dev, sandbox."
  }
}

variable "extra_tags" {
  description = "Additional tags to merge with the default common_tags on all resources."
  type        = map(string)
  default     = {}
}

# ── OpenSearch ────────────────────────────────────────────────────────────────
variable "opensearch_domain_name" {
  description = "Name of the existing Amazon OpenSearch Service domain to use as the OSIS sink."
  type        = string
}

variable "opensearch_version" {
  description = "OpenSearch version string for AMG data source config (e.g. '2.13.0')."
  type        = string
  default     = "2.13.0"
}

# ── AMP ───────────────────────────────────────────────────────────────────────
variable "amp_alarm_error_threshold" {
  description = "Number of AMP ingestion errors per 5 min to trigger the CloudWatch alarm."
  type        = number
  default     = 5
}

variable "alarm_sns_topic_arn" {
  description = "SNS topic ARN for infrastructure alarms (AMP ingestion errors, etc.). Set to null to disable."
  type        = string
  default     = null
}

# ── OSIS ──────────────────────────────────────────────────────────────────────
variable "osis_min_units" {
  description = "Minimum Ingestion Capacity Units per OSIS pipeline."
  type        = number
  default     = 1
}

variable "osis_max_units" {
  description = "Maximum Ingestion Capacity Units per OSIS pipeline (autoscaling ceiling)."
  type        = number
  default     = 4
}

variable "enable_amp_metrics_fanout" {
  description = "Fan-out OTLP metrics from the OSIS metrics pipeline to AMP."
  type        = bool
  default     = true
}

variable "osis_pipeline_arn_override" {
  description = <<EOT
Set after first apply to tighten the collector OSIS Ingest policy.
Leave null on first apply — the policy will use '*' (bootstrapping).
After first apply, set to a comma-separated string or use the output from module.osis.
EOT
  type        = string
  default     = null
}

# ── AMG ───────────────────────────────────────────────────────────────────────
variable "grafana_version" {
  description = "Grafana version for the AMG workspace."
  type        = string
  default     = "10.4"
}

variable "amg_authentication_providers" {
  description = "Authentication providers for the AMG workspace (AWS_SSO, SAML, or both)."
  type        = list(string)
  default     = ["AWS_SSO"]
}

variable "amg_permission_type" {
  description = "AMG permission type: SERVICE_MANAGED or CUSTOMER_MANAGED."
  type        = string
  default     = "SERVICE_MANAGED"
}

variable "amg_enable_sns_notifications" {
  description = "Enable SNS as a Grafana notification destination."
  type        = bool
  default     = false
}

variable "amg_token_ttl_seconds" {
  description = "TTL in seconds for the AMG Terraform service account token."
  type        = number
  default     = 2592000   # 30 days
}

# ── IAM / EKS ─────────────────────────────────────────────────────────────────
variable "eks_oidc_provider_arn" {
  description = "EKS OIDC provider ARN for IRSA. Set to null if not using EKS."
  type        = string
  default     = null
}

variable "eks_namespace" {
  description = "Kubernetes namespace of the OTel Collector (for IRSA)."
  type        = string
  default     = "dataobs"
}

variable "eks_service_account_name" {
  description = "Kubernetes service account name for the OTel Collector (for IRSA)."
  type        = string
  default     = "dataobs-otel-collector"
}

# ── Shared ────────────────────────────────────────────────────────────────────
variable "log_retention_days" {
  description = "CloudWatch log retention in days for OSIS and AMP log groups."
  type        = number
  default     = 90
}
