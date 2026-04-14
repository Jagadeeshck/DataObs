output "workspace_id" {
  description = "ID of the AMP workspace."
  value       = aws_prometheus_workspace.this.id
}

output "workspace_arn" {
  description = "ARN of the AMP workspace. Pass to the IAM module as amp_workspace_arn."
  value       = aws_prometheus_workspace.this.arn
}

output "prometheus_endpoint" {
  description = "Base URL of the AMP workspace (e.g. https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-xxx/)."
  value       = aws_prometheus_workspace.this.prometheus_endpoint
}

output "remote_write_url" {
  description = "Full Prometheus Remote Write URL. Set as AMP_REMOTE_WRITE_URL env var on the OTel Collector."
  value       = "${aws_prometheus_workspace.this.prometheus_endpoint}api/v1/remote_write"
}

output "query_url" {
  description = "Full Prometheus query URL for Grafana data source configuration."
  value       = "${aws_prometheus_workspace.this.prometheus_endpoint}api/v1/query"
}

output "log_group_arn" {
  description = "ARN of the CloudWatch log group for AMP logs (null if logging disabled)."
  value       = var.enable_logging ? aws_cloudwatch_log_group.amp[0].arn : null
}

output "ssm_remote_write_url_path" {
  description = "SSM Parameter path storing the AMP remote write URL."
  value       = aws_ssm_parameter.amp_remote_write_url.name
}
