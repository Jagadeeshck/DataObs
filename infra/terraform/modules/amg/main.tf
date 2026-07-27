# =============================================================================
# DataObs — Amazon Managed Grafana (AMG) Module
# =============================================================================
# Creates:
#   - AMG workspace (Grafana v10, SSO or SAML auth)
#   - Service account + token for Terraform automation (stored in Secrets Manager)
#   - Grafana data sources (AMP, Amazon OpenSearch, X-Ray, CloudWatch)
#   - Grafana folders for DataObs dashboards
#   - Optional: SNS alert notification channel
#
# Auth note: AMG requires AWS IAM Identity Center (SSO) enabled in the account
# for SERVICE_MANAGED permission type. If SSO is not available, set
# permission_type = "CUSTOMER_MANAGED" and supply your own IAM role.
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    grafana = {
      source  = "grafana/grafana"
      version = ">= 3.0"
    }
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# ── AMG Workspace ─────────────────────────────────────────────────────────────
resource "aws_grafana_workspace" "this" {
  name        = var.workspace_name
  description = var.workspace_description

  # Authentication: AWS SSO (default) or SAML
  authentication_providers = var.authentication_providers

  # Permission type: SERVICE_MANAGED lets AMG create IAM roles automatically.
  # CUSTOMER_MANAGED requires supplying role_arn.
  permission_type = var.permission_type
  role_arn        = var.permission_type == "CUSTOMER_MANAGED" ? var.workspace_role_arn : null

  account_access_type = "CURRENT_ACCOUNT"
  grafana_version     = var.grafana_version

  # Enable the data sources DataObs uses
  data_sources = [
    "PROMETHEUS", # AMP
    "AMAZON_OPENSEARCH_SERVICE",
    "CLOUDWATCH",
    "XRAY",
  ]

  notification_destinations = var.enable_sns_notifications ? ["SNS"] : []

  tags = merge(var.tags, {
    Name   = var.workspace_name
    Module = "dataobs-amg"
  })
}

# ── Service Account for Terraform automation ─────────────────────────────────
resource "aws_grafana_workspace_service_account" "terraform" {
  name         = "dataobs-terraform"
  grafana_role = "ADMIN"
  workspace_id = aws_grafana_workspace.this.id
}

resource "aws_grafana_workspace_service_account_token" "terraform" {
  name               = "dataobs-terraform-token"
  service_account_id = aws_grafana_workspace_service_account.terraform.service_account_id
  workspace_id       = aws_grafana_workspace.this.id
  seconds_to_live    = var.service_account_token_ttl_seconds
}

# ── Store service account token in Secrets Manager ───────────────────────────
resource "aws_secretsmanager_secret" "grafana_token" {
  name                    = "dataobs/amg/service-account-token"
  description             = "DataObs AMG Terraform service account token"
  recovery_window_in_days = 7
  tags                    = var.tags
}

resource "aws_secretsmanager_secret_version" "grafana_token" {
  secret_id = aws_secretsmanager_secret.grafana_token.id
  secret_string = jsonencode({
    token         = aws_grafana_workspace_service_account_token.terraform.key
    workspace_id  = aws_grafana_workspace.this.id
    workspace_url = "https://${aws_grafana_workspace.this.endpoint}"
  })
}

# ── Grafana provider — uses service account token ────────────────────────────
# The grafana provider is configured here and passed to data-source resources.
# This avoids a provider-in-module anti-pattern by using provider aliasing.
provider "grafana" {
  alias = "amg"
  url   = "https://${aws_grafana_workspace.this.endpoint}"
  auth  = aws_grafana_workspace_service_account_token.terraform.key
}

# ── Grafana Folder: DataObs ───────────────────────────────────────────────────
resource "grafana_folder" "dataobs" {
  provider = grafana.amg
  title    = "DataObs"

  depends_on = [aws_grafana_workspace_service_account_token.terraform]
}

# ── Data Source: Amazon Managed Prometheus (Metrics) ─────────────────────────
resource "grafana_data_source" "amp" {
  provider   = grafana.amg
  name       = "DataObs — AMP (Metrics)"
  type       = "prometheus"
  uid        = "dataobs-amp"
  is_default = true

  url = var.amp_workspace_url # https://aps-workspaces.<region>.amazonaws.com/workspaces/<id>/

  json_data_encoded = jsonencode({
    httpMethod    = "POST"
    sigV4Auth     = true
    sigV4AuthType = "workspace-iam-role"
    sigV4Region   = data.aws_region.current.name
    timeInterval  = "30s"
    queryTimeout  = "60s"
    # Wire exemplars → trace data source for click-through from metrics to traces
    exemplarTraceIdDestinations = [{
      name          = "trace_id"
      datasourceUid = "dataobs-os-traces"
    }]
  })

  depends_on = [aws_grafana_workspace_service_account_token.terraform]
}

# ── Data Source: Amazon OpenSearch Service (Traces) ──────────────────────────
resource "grafana_data_source" "opensearch_traces" {
  provider = grafana.amg
  name     = "DataObs — OpenSearch (Traces)"
  type     = "grafana-opensearch-datasource"
  uid      = "dataobs-os-traces"

  url = var.opensearch_domain_endpoint

  json_data_encoded = jsonencode({
    database        = "trace-analytics-raw"
    logMessageField = "body"
    logLevelField   = "severity"
    version         = var.opensearch_version
    flavor          = "opensearch"
    timeField       = "@timestamp"
    sigV4Auth       = true
    sigV4Region     = data.aws_region.current.name
    sigV4AuthType   = "workspace-iam-role"
  })

  depends_on = [aws_grafana_workspace_service_account_token.terraform]
}

# ── Data Source: Amazon OpenSearch Service (Logs) ────────────────────────────
resource "grafana_data_source" "opensearch_logs" {
  provider = grafana.amg
  name     = "DataObs — OpenSearch (Logs)"
  type     = "grafana-opensearch-datasource"
  uid      = "dataobs-os-logs"

  url = var.opensearch_domain_endpoint

  json_data_encoded = jsonencode({
    database        = "dataobs-logs-*"
    logMessageField = "body"
    logLevelField   = "attributes.log.level"
    version         = var.opensearch_version
    flavor          = "opensearch"
    timeField       = "@timestamp"
    sigV4Auth       = true
    sigV4Region     = data.aws_region.current.name
    sigV4AuthType   = "workspace-iam-role"
  })

  depends_on = [aws_grafana_workspace_service_account_token.terraform]
}

# ── Data Source: AWS X-Ray (native AMG integration) ──────────────────────────
resource "grafana_data_source" "xray" {
  provider = grafana.amg
  name     = "DataObs — X-Ray (Traces)"
  type     = "grafana-x-ray-datasource"
  uid      = "dataobs-xray"

  json_data_encoded = jsonencode({
    authType      = "workspace-iam-role"
    defaultRegion = data.aws_region.current.name
  })

  depends_on = [aws_grafana_workspace_service_account_token.terraform]
}

# ── Data Source: CloudWatch ───────────────────────────────────────────────────
resource "grafana_data_source" "cloudwatch" {
  provider = grafana.amg
  name     = "DataObs — CloudWatch"
  type     = "cloudwatch"
  uid      = "dataobs-cloudwatch"

  json_data_encoded = jsonencode({
    authType      = "workspace-iam-role"
    defaultRegion = data.aws_region.current.name
  })

  depends_on = [aws_grafana_workspace_service_account_token.terraform]
}

# ── SSM Parameter: AMG endpoint ──────────────────────────────────────────────
resource "aws_ssm_parameter" "amg_endpoint" {
  name        = "/${var.name_prefix}/amg/workspace-url"
  type        = "String"
  value       = "https://${aws_grafana_workspace.this.endpoint}"
  description = "DataObs Amazon Managed Grafana workspace URL"
  tags        = var.tags
}
