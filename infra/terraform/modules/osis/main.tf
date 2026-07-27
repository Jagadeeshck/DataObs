# =============================================================================
# DataObs — Amazon OpenSearch Ingestion (OSIS) Module
# =============================================================================
# Creates three OSIS pipelines, one per signal type:
#   - dataobs-traces  : OTLP traces → OpenSearch trace-analytics-raw + service-map
#   - dataobs-logs    : OTLP logs   → OpenSearch dataobs-logs-* (daily rolling)
#   - dataobs-metrics : OTLP metrics → OpenSearch + optional AMP fan-out
#
# Each pipeline uses the OTLP HTTP source and SigV4-authenticated OpenSearch sink.
# The pipeline configuration bodies are templated so all endpoint/role/region
# values are injected at plan time — no manual edits to YAML needed.
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.36" # aws_osis_pipeline GA'd in 5.36
    }
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# ── CloudWatch Log Groups ─────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "traces" {
  name              = "/aws/vendedlogs/OpenSearchIngestion/${var.name_prefix}-traces"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "logs" {
  name              = "/aws/vendedlogs/OpenSearchIngestion/${var.name_prefix}-logs"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "metrics" {
  name              = "/aws/vendedlogs/OpenSearchIngestion/${var.name_prefix}-metrics"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# ── OSIS Pipeline: Traces ─────────────────────────────────────────────────────
resource "aws_osis_pipeline" "traces" {
  pipeline_name = "${var.name_prefix}-traces"
  min_units     = var.min_units
  max_units     = var.max_units

  pipeline_configuration_body = templatefile("${path.module}/templates/traces-pipeline.yaml.tftpl", {
    opensearch_endpoint = var.opensearch_domain_endpoint
    pipeline_role_arn   = var.pipeline_role_arn
    region              = data.aws_region.current.name
  })

  log_publishing_options {
    is_logging_enabled = true
    cloudwatch_log_destination {
      log_group = aws_cloudwatch_log_group.traces.name
    }
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-traces", Signal = "traces" })
}

# ── OSIS Pipeline: Logs ───────────────────────────────────────────────────────
resource "aws_osis_pipeline" "logs" {
  pipeline_name = "${var.name_prefix}-logs"
  min_units     = var.min_units
  max_units     = var.max_units

  pipeline_configuration_body = templatefile("${path.module}/templates/logs-pipeline.yaml.tftpl", {
    opensearch_endpoint = var.opensearch_domain_endpoint
    pipeline_role_arn   = var.pipeline_role_arn
    region              = data.aws_region.current.name
  })

  log_publishing_options {
    is_logging_enabled = true
    cloudwatch_log_destination {
      log_group = aws_cloudwatch_log_group.logs.name
    }
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-logs", Signal = "logs" })
}

# ── OSIS Pipeline: Metrics ────────────────────────────────────────────────────
resource "aws_osis_pipeline" "metrics" {
  pipeline_name = "${var.name_prefix}-metrics"
  min_units     = var.min_units
  max_units     = var.max_units

  pipeline_configuration_body = templatefile("${path.module}/templates/metrics-pipeline.yaml.tftpl", {
    opensearch_endpoint  = var.opensearch_domain_endpoint
    pipeline_role_arn    = var.pipeline_role_arn
    region               = data.aws_region.current.name
    amp_remote_write_url = var.amp_remote_write_url
    amp_role_arn         = var.pipeline_role_arn # same role with aps:RemoteWrite
    enable_amp_fanout    = var.enable_amp_metrics_fanout
  })

  log_publishing_options {
    is_logging_enabled = true
    cloudwatch_log_destination {
      log_group = aws_cloudwatch_log_group.metrics.name
    }
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-metrics", Signal = "metrics" })
}

# ── SSM Parameters: OSIS Ingest Endpoints ─────────────────────────────────────
# Store the ingestion URLs so OTel Collector on EC2/ECS can resolve them at runtime.
resource "aws_ssm_parameter" "osis_traces_endpoint" {
  name        = "/${var.name_prefix}/osis/traces-endpoint"
  type        = "String"
  value       = tolist(aws_osis_pipeline.traces.ingest_endpoint_urls)[0]
  description = "DataObs OSIS traces pipeline ingestion endpoint"
  tags        = var.tags
}

resource "aws_ssm_parameter" "osis_logs_endpoint" {
  name        = "/${var.name_prefix}/osis/logs-endpoint"
  type        = "String"
  value       = tolist(aws_osis_pipeline.logs.ingest_endpoint_urls)[0]
  description = "DataObs OSIS logs pipeline ingestion endpoint"
  tags        = var.tags
}

resource "aws_ssm_parameter" "osis_metrics_endpoint" {
  name        = "/${var.name_prefix}/osis/metrics-endpoint"
  type        = "String"
  value       = tolist(aws_osis_pipeline.metrics.ingest_endpoint_urls)[0]
  description = "DataObs OSIS metrics pipeline ingestion endpoint"
  tags        = var.tags
}
