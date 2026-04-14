output "collector_role_arn" {
  description = "ARN of the OTel Collector IAM role (attach to EC2 instance profile / ECS task role / EKS IRSA annotation)."
  value       = aws_iam_role.collector.arn
}

output "collector_role_name" {
  description = "Name of the OTel Collector IAM role."
  value       = aws_iam_role.collector.name
}

output "collector_instance_profile_arn" {
  description = "ARN of the EC2 instance profile for the OTel Collector role."
  value       = aws_iam_instance_profile.collector.arn
}

output "collector_instance_profile_name" {
  description = "Name of the EC2 instance profile for the OTel Collector role."
  value       = aws_iam_instance_profile.collector.name
}

output "osis_pipeline_role_arn" {
  description = "ARN of the OSIS pipeline IAM role. Pass to aws_osis_pipeline resource as the pipeline role."
  value       = aws_iam_role.osis_pipeline.arn
}

output "osis_pipeline_role_name" {
  description = "Name of the OSIS pipeline IAM role."
  value       = aws_iam_role.osis_pipeline.name
}

output "amg_role_arn" {
  description = "ARN of the Amazon Managed Grafana workspace IAM role."
  value       = aws_iam_role.amg.arn
}

output "amg_role_name" {
  description = "Name of the Amazon Managed Grafana workspace IAM role."
  value       = aws_iam_role.amg.name
}

output "amp_write_policy_arn" {
  description = "ARN of the AMP RemoteWrite policy (attach to additional roles if needed)."
  value       = aws_iam_policy.amp_write.arn
}

output "osis_ingest_policy_arn" {
  description = "ARN of the OSIS Ingest policy (attach to additional roles if needed)."
  value       = aws_iam_policy.osis_ingest.arn
}
