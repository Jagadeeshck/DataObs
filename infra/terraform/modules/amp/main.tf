# =============================================================================
# DataObs — Amazon Managed Prometheus (AMP) Module
# =============================================================================
# Creates:
#   - AMP workspace (remote write + query endpoint)
#   - CloudWatch alarm on ingestion errors
#   - SSM Parameter with workspace URL (for use by OTel Collector env var)
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# ── AMP Workspace ─────────────────────────────────────────────────────────────
resource "aws_prometheus_workspace" "this" {
  alias = var.workspace_alias

  # Logging to CloudWatch (optional — set log_group_name to enable)
  dynamic "logging_configuration" {
    for_each = var.log_group_arn != null ? [1] : []
    content {
      log_group_arn = "${var.log_group_arn}:*"
    }
  }

  tags = merge(var.tags, {
    Name   = var.workspace_alias
    Module = "dataobs-amp"
  })
}

# ── CloudWatch Log Group for AMP logs ────────────────────────────────────────
resource "aws_cloudwatch_log_group" "amp" {
  count             = var.enable_logging ? 1 : 0
  name              = "/aws/prometheus/${var.name_prefix}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# ── Alert: AMP ingestion error rate ─────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "amp_ingestion_errors" {
  alarm_name          = "${var.name_prefix}-amp-ingestion-errors"
  alarm_description   = "DataObs AMP: remote write ingestion errors exceeded threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RemoteWriteInvalidRequests"
  namespace           = "AWS/Prometheus"
  period              = 300
  statistic           = "Sum"
  threshold           = var.alarm_ingestion_error_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    WorkspaceId = aws_prometheus_workspace.this.id
  }

  alarm_actions = var.alarm_sns_topic_arn != null ? [var.alarm_sns_topic_arn] : []
  ok_actions    = var.alarm_sns_topic_arn != null ? [var.alarm_sns_topic_arn] : []

  tags = var.tags
}

# ── SSM Parameter: Remote Write URL ─────────────────────────────────────────
# Stored so that OTel Collector on EC2 / ECS can resolve it at runtime.
resource "aws_ssm_parameter" "amp_remote_write_url" {
  name        = "/${var.name_prefix}/amp/remote-write-url"
  type        = "String"
  value       = "${aws_prometheus_workspace.this.prometheus_endpoint}api/v1/remote_write"
  description = "DataObs AMP remote write endpoint for OTel Collector"
  tags        = var.tags
}

resource "aws_ssm_parameter" "amp_workspace_id" {
  name        = "/${var.name_prefix}/amp/workspace-id"
  type        = "String"
  value       = aws_prometheus_workspace.this.id
  description = "DataObs AMP workspace ID"
  tags        = var.tags
}
