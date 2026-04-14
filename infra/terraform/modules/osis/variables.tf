variable "name_prefix" {
  description = "Prefix for pipeline names and resource names (e.g. 'dataobs-prod'). Must match pattern [a-z][a-z0-9\\-]+."
  type        = string
  default     = "dataobs"

  validation {
    condition     = can(regex("^[a-z][a-z0-9\\-]+$", var.name_prefix))
    error_message = "name_prefix must start with a lowercase letter and contain only lowercase letters, digits, and hyphens."
  }
}

variable "opensearch_domain_endpoint" {
  description = "HTTPS endpoint of the Amazon OpenSearch Service domain (without trailing slash), e.g. https://search-mydom-xyz.us-east-1.es.amazonaws.com."
  type        = string
}

variable "pipeline_role_arn" {
  description = "ARN of the IAM role the OSIS pipelines will assume (output of the iam module: osis_pipeline_role_arn)."
  type        = string
}

variable "min_units" {
  description = "Minimum Ingestion Capacity Units (ICUs) per pipeline. Each ICU ~1 vCPU + 2 GB RAM."
  type        = number
  default     = 1

  validation {
    condition     = var.min_units >= 1 && var.min_units <= 96
    error_message = "min_units must be between 1 and 96."
  }
}

variable "max_units" {
  description = "Maximum Ingestion Capacity Units (ICUs) per pipeline. OSIS autoscales between min and max."
  type        = number
  default     = 4

  validation {
    condition     = var.max_units >= 1 && var.max_units <= 96
    error_message = "max_units must be between 1 and 96."
  }
}

variable "log_retention_days" {
  description = "Retention period in days for OSIS CloudWatch log groups."
  type        = number
  default     = 90
}

variable "amp_remote_write_url" {
  description = "AMP Remote Write URL for metrics fan-out. Required when enable_amp_metrics_fanout=true."
  type        = string
  default     = ""
}

variable "enable_amp_metrics_fanout" {
  description = "Fan-out OTLP metrics to AMP as well as OpenSearch from the metrics pipeline."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all OSIS resources."
  type        = map(string)
  default     = {}
}
