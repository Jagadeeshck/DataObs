# =============================================================================
# DataObs — Tenant-Side Elasticsearch: Input Variables
# =============================================================================

variable "tenant_id" {
  description = "Unique tenant identifier (alphanumeric, lowercase, max 28 chars — used in domain name)"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9]{1,28}$", var.tenant_id))
    error_message = "tenant_id must be 1-28 lowercase alphanumeric characters."
  }
}

variable "tenant_vpc_id" {
  description = "VPC ID of the tenant's AWS environment"
  type        = string
}

variable "tenant_vpc_cidr" {
  description = "CIDR block of the tenant VPC — restricts ES inbound to this range"
  type        = string
}

variable "tenant_subnet_id" {
  description = "Single private subnet ID in the tenant VPC for the OpenSearch domain"
  type        = string
}

variable "server_es_sg_id" {
  description = "Security group ID of the server-side OpenSearch cluster (for CCR inbound)"
  type        = string
}

variable "server_es_endpoint" {
  description = "HTTPS endpoint of the server-side OpenSearch cluster"
  type        = string
}

variable "tenant_es_master_user" {
  description = "Master username for the tenant OpenSearch domain (FGAC)"
  type        = string
  sensitive   = true
}

variable "tenant_es_master_password" {
  description = "Master password for the tenant OpenSearch domain (FGAC)"
  type        = string
  sensitive   = true
}

variable "tenant_es_api_key" {
  description = "Pre-generated Elasticsearch API key for this tenant's OTel collector"
  type        = string
  sensitive   = true
}

variable "tenant_allowed_role_arns" {
  description = "IAM role ARNs in the tenant account allowed to call es:* on this domain"
  type        = list(string)
}

variable "tenant_node_instance_type" {
  description = "OpenSearch instance type for the tenant domain"
  type        = string
  default     = "t3.medium.search"
}

variable "tenant_volume_gb" {
  description = "EBS volume size for the tenant domain (GiB)"
  type        = number
  default     = 100
}

variable "common_tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default = {
    Project   = "DataObs"
    ManagedBy = "Terraform"
    Tier      = "tenant"
  }
}
