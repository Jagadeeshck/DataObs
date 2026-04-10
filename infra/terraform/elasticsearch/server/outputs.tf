# =============================================================================
# DataObs — Server-Side Elasticsearch: Outputs
# =============================================================================

output "endpoint" {
  description = "HTTPS endpoint of the server-side OpenSearch domain"
  value       = "https://${aws_opensearch_domain.dataobs_server.endpoint}"
}

output "domain_arn" {
  description = "ARN of the server-side OpenSearch domain"
  value       = aws_opensearch_domain.dataobs_server.arn
}

output "domain_name" {
  description = "Name of the server-side OpenSearch domain"
  value       = aws_opensearch_domain.dataobs_server.domain_name
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for encryption at rest"
  value       = aws_kms_key.dataobs_es.arn
}

output "snapshot_bucket_name" {
  description = "S3 bucket used for ES snapshots"
  value       = aws_s3_bucket.dataobs_es_snapshots.bucket
}

output "security_group_id" {
  description = "Security group ID of the OpenSearch domain"
  value       = aws_security_group.dataobs_es.id
}
