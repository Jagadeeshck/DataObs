# =============================================================================
# DataObs — Server-Side Elasticsearch: Input Variables
# =============================================================================

variable "vpc_id" {
  description = "VPC ID where the OpenSearch domain will be placed"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs across 3 AZs for the OpenSearch domain"
  type        = list(string)
  validation {
    condition     = length(var.private_subnet_ids) == 3
    error_message = "Exactly 3 private subnet IDs are required (one per AZ)."
  }
}

variable "otel_collector_sg_id" {
  description = "Security group ID of the OTel collector fleet"
  type        = string
}

variable "dataobs_api_sg_id" {
  description = "Security group ID of the DataObs API service"
  type        = string
}

variable "allowed_iam_role_arns" {
  description = "List of IAM role ARNs allowed to call es:* on the domain"
  type        = list(string)
}

variable "es_master_user" {
  description = "Fine-grained access control master username (stored in Secrets Manager)"
  type        = string
  sensitive   = true
}

variable "es_master_password" {
  description = "Fine-grained access control master password (stored in Secrets Manager)"
  type        = string
  sensitive   = true
}

variable "data_node_instance_type" {
  description = "Instance type for hot data nodes"
  type        = string
  default     = "r6g.large.search"
}

variable "master_node_instance_type" {
  description = "Instance type for dedicated master nodes"
  type        = string
  default     = "m6g.large.search"
}

variable "warm_node_instance_type" {
  description = "Instance type for warm data nodes"
  type        = string
  default     = "ultrawarm1.medium.search"
}

variable "data_node_volume_gb" {
  description = "EBS volume size per hot data node (GiB)"
  type        = number
  default     = 500
}

variable "alarm_sns_arns" {
  description = "SNS topic ARNs to notify on CloudWatch alarms"
  type        = list(string)
  default     = []
}

variable "common_tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default = {
    Project   = "DataObs"
    ManagedBy = "Terraform"
    Tier      = "server"
  }
}
