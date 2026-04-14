output "workspace_id" {
  description = "ID of the AMG workspace."
  value       = aws_grafana_workspace.this.id
}

output "workspace_arn" {
  description = "ARN of the AMG workspace."
  value       = aws_grafana_workspace.this.arn
}

output "workspace_endpoint" {
  description = "Hostname of the AMG workspace (without https://). Use workspace_url for the full URL."
  value       = aws_grafana_workspace.this.endpoint
}

output "workspace_url" {
  description = "Full HTTPS URL of the AMG workspace. Open this in a browser to access Grafana."
  value       = "https://${aws_grafana_workspace.this.endpoint}"
}

output "grafana_version" {
  description = "Version of Grafana running on the workspace."
  value       = aws_grafana_workspace.this.grafana_version
}

output "service_account_token_secret_arn" {
  description = "ARN of the Secrets Manager secret holding the Grafana service account token."
  value       = aws_secretsmanager_secret.grafana_token.arn
  sensitive   = true
}

output "amp_datasource_uid" {
  description = "UID of the provisioned AMP data source in Grafana."
  value       = grafana_data_source.amp.uid
}

output "opensearch_traces_datasource_uid" {
  description = "UID of the provisioned OpenSearch traces data source in Grafana."
  value       = grafana_data_source.opensearch_traces.uid
}

output "opensearch_logs_datasource_uid" {
  description = "UID of the provisioned OpenSearch logs data source in Grafana."
  value       = grafana_data_source.opensearch_logs.uid
}

output "dataobs_folder_id" {
  description = "ID of the 'DataObs' Grafana folder for dashboard imports."
  value       = grafana_folder.dataobs.id
}

output "ssm_workspace_url_path" {
  description = "SSM Parameter path storing the AMG workspace URL."
  value       = aws_ssm_parameter.amg_endpoint.name
}
