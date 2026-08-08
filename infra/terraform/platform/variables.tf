variable "cluster_id" { type = string; validation { condition = can(regex("^[a-z][a-z0-9-]{2,62}$", var.cluster_id)); error_message = "cluster_id must be a bounded DNS label" } }
variable "region" { type = string }
variable "private_subnet_ids" { type = list(string); validation { condition = length(var.private_subnet_ids) >= 3; error_message = "reference HA topology requires at least three private subnets" } }
variable "external_elasticsearch_connection_reference" { type = string; sensitive = true }
variable "otlp_endpoint_reference" { type = string; sensitive = true }
variable "tags" { type = map(string); default = {} }
