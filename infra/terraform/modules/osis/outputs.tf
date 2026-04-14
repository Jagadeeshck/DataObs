output "traces_pipeline_arn" {
  description = "ARN of the OSIS traces pipeline. Pass to iam module as osis_pipeline_arn."
  value       = aws_osis_pipeline.traces.pipeline_arn
}

output "logs_pipeline_arn" {
  description = "ARN of the OSIS logs pipeline."
  value       = aws_osis_pipeline.logs.pipeline_arn
}

output "metrics_pipeline_arn" {
  description = "ARN of the OSIS metrics pipeline."
  value       = aws_osis_pipeline.metrics.pipeline_arn
}

output "traces_ingest_endpoint" {
  description = "Ingestion URL for the traces pipeline. Set as OSIS_TRACES_ENDPOINT env var on the OTel Collector."
  value       = tolist(aws_osis_pipeline.traces.ingest_endpoint_urls)[0]
}

output "logs_ingest_endpoint" {
  description = "Ingestion URL for the logs pipeline. Set as OSIS_LOGS_ENDPOINT env var on the OTel Collector."
  value       = tolist(aws_osis_pipeline.logs.ingest_endpoint_urls)[0]
}

output "metrics_ingest_endpoint" {
  description = "Ingestion URL for the metrics pipeline. Set as OSIS_METRICS_ENDPOINT env var on the OTel Collector."
  value       = tolist(aws_osis_pipeline.metrics.ingest_endpoint_urls)[0]
}

output "ssm_traces_endpoint_path" {
  description = "SSM Parameter path for the traces ingestion endpoint."
  value       = aws_ssm_parameter.osis_traces_endpoint.name
}

output "ssm_logs_endpoint_path" {
  description = "SSM Parameter path for the logs ingestion endpoint."
  value       = aws_ssm_parameter.osis_logs_endpoint.name
}

output "ssm_metrics_endpoint_path" {
  description = "SSM Parameter path for the metrics ingestion endpoint."
  value       = aws_ssm_parameter.osis_metrics_endpoint.name
}
