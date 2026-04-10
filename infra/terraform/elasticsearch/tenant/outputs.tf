# =============================================================================
# DataObs — Tenant-Side Elasticsearch: Outputs
# =============================================================================

output "tenant_endpoint" {
  description = "HTTPS endpoint of the tenant OpenSearch domain"
  value       = "https://${aws_opensearch_domain.tenant.endpoint}"
}

output "tenant_domain_arn" {
  description = "ARN of the tenant OpenSearch domain"
  value       = aws_opensearch_domain.tenant.arn
}

output "tenant_domain_name" {
  description = "Name of the tenant OpenSearch domain"
  value       = aws_opensearch_domain.tenant.domain_name
}

output "api_key_secret_arn" {
  description = "Secrets Manager ARN storing the tenant API key + endpoint"
  value       = aws_secretsmanager_secret.tenant_es_api_key.arn
}
