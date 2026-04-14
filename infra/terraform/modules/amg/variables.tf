variable "name_prefix" {
  description = "Prefix for resource names (e.g. 'dataobs-prod')."
  type        = string
  default     = "dataobs"
}

variable "workspace_name" {
  description = "Name of the AMG workspace."
  type        = string
  default     = "dataobs-grafana"
}

variable "workspace_description" {
  description = "Description of the AMG workspace."
  type        = string
  default     = "DataObs — Cloud-agnostic data observability platform dashboards"
}

variable "grafana_version" {
  description = "Grafana version to run. Available: '9.4', '10.4'. Defaults to latest available."
  type        = string
  default     = "10.4"
}

variable "authentication_providers" {
  description = "Authentication providers for the workspace. Valid values: AWS_SSO, SAML. AWS_SSO requires IAM Identity Center enabled."
  type        = list(string)
  default     = ["AWS_SSO"]

  validation {
    condition     = length([for p in var.authentication_providers : p if !contains(["AWS_SSO", "SAML"], p)]) == 0
    error_message = "authentication_providers must contain only 'AWS_SSO' and/or 'SAML'."
  }
}

variable "permission_type" {
  description = "Permission type: SERVICE_MANAGED (AMG creates IAM roles) or CUSTOMER_MANAGED (supply workspace_role_arn)."
  type        = string
  default     = "SERVICE_MANAGED"

  validation {
    condition     = contains(["SERVICE_MANAGED", "CUSTOMER_MANAGED"], var.permission_type)
    error_message = "permission_type must be SERVICE_MANAGED or CUSTOMER_MANAGED."
  }
}

variable "workspace_role_arn" {
  description = "IAM role ARN for CUSTOMER_MANAGED permission type. Output of iam module: amg_role_arn."
  type        = string
  default     = null
}

variable "enable_sns_notifications" {
  description = "Enable SNS as a notification destination (for Grafana alerting)."
  type        = bool
  default     = false
}

variable "service_account_token_ttl_seconds" {
  description = "TTL in seconds for the Terraform service account token. Rotate before expiry."
  type        = number
  default     = 2592000   # 30 days
}

variable "amp_workspace_url" {
  description = "AMP workspace base URL, e.g. https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-xxx/. Output of amp module: prometheus_endpoint."
  type        = string
}

variable "opensearch_domain_endpoint" {
  description = "HTTPS endpoint of the Amazon OpenSearch Service domain, e.g. https://search-mydom-xyz.us-east-1.es.amazonaws.com."
  type        = string
}

variable "opensearch_version" {
  description = "OpenSearch version string for the Grafana data source plugin (e.g. '2.13.0')."
  type        = string
  default     = "2.13.0"
}

variable "tags" {
  description = "Tags to apply to all AMG resources."
  type        = map(string)
  default     = {}
}
