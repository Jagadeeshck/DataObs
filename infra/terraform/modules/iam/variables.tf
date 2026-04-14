variable "name_prefix" {
  description = "Prefix for all IAM resource names (e.g. 'dataobs-prod')."
  type        = string
  default     = "dataobs"
}

variable "amp_workspace_arn" {
  description = "ARN of the AMP workspace. Used in collector RemoteWrite and AMG query policies."
  type        = string
}

variable "osis_pipeline_arn" {
  description = "ARN of the OSIS pipeline. Used in collector Ingest policy. Set to '*' before pipeline is created, then tighten post-deploy."
  type        = string
  default     = "*"
}

variable "opensearch_domain_arn" {
  description = "ARN of the Amazon OpenSearch Service domain (e.g. arn:aws:es:us-east-1:123:domain/dataobs-os)."
  type        = string
}

variable "eks_oidc_provider_arn" {
  description = "ARN of the EKS OIDC provider for IRSA. Set to null if not using EKS."
  type        = string
  default     = null
}

variable "eks_namespace" {
  description = "Kubernetes namespace where the OTel Collector runs."
  type        = string
  default     = "dataobs"
}

variable "eks_service_account_name" {
  description = "Kubernetes service account name for the OTel Collector."
  type        = string
  default     = "dataobs-otel-collector"
}

variable "tags" {
  description = "Tags to apply to all IAM resources."
  type        = map(string)
  default     = {}
}
