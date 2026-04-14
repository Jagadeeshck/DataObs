# =============================================================================
# DataObs — AWS Backend Root Module
# =============================================================================
# Composes the four child modules into a full AWS observability backend:
#
#   AMP workspace          → metrics sink for OTel Collector
#   OSIS pipelines (×3)   → traces / logs / metrics → OpenSearch + AMP
#   AMG workspace          → Grafana dashboards consuming AMP + OpenSearch
#   IAM roles              → OTel Collector, OSIS pipeline, AMG workspace
#
# Prerequisites:
#   - Amazon OpenSearch Service domain already provisioned
#     (use infra/terraform/elasticsearch/ or the opensearch module separately)
#   - AWS IAM Identity Center (SSO) enabled in the account (for AMG)
#   - Terraform S3 backend bucket exists (see backend.tf.example)
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.36"
    }
    grafana = {
      source  = "grafana/grafana"
      version = ">= 3.0"
    }
  }

  # Uncomment and configure for team use:
  # backend "s3" {
  #   bucket         = "your-tfstate-bucket"
  #   key            = "dataobs/aws-backend/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(local.common_tags, var.extra_tags)
  }
}

# ── Data sources ──────────────────────────────────────────────────────────────
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_opensearch_domain" "dataobs" {
  domain_name = var.opensearch_domain_name
}

# ── Local computed values ──────────────────────────────────────────────────────
locals {
  common_tags = {
    Project     = "DataObs"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Module      = "aws-backend"
  }

  name_prefix = "${var.name_prefix}-${var.environment}"
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. AMP Workspace
# ─────────────────────────────────────────────────────────────────────────────
module "amp" {
  source = "../modules/amp"

  name_prefix     = local.name_prefix
  workspace_alias = "${local.name_prefix}-metrics"
  enable_logging  = true
  log_retention_days            = var.log_retention_days
  alarm_ingestion_error_threshold = var.amp_alarm_error_threshold
  alarm_sns_topic_arn           = var.alarm_sns_topic_arn

  tags = local.common_tags
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. IAM Roles
# Created after AMP (needs AMP ARN) but before OSIS (OSIS needs role ARN).
# Uses a placeholder for osis_pipeline_arn on first apply — tighten post-deploy.
# ─────────────────────────────────────────────────────────────────────────────
module "iam" {
  source = "../modules/iam"

  name_prefix           = local.name_prefix
  amp_workspace_arn     = module.amp.workspace_arn
  opensearch_domain_arn = data.aws_opensearch_domain.dataobs.arn

  # OSIS pipeline ARN is not known until the osis module runs.
  # On first apply: leave as '*' (broad, acceptable for bootstrap).
  # After first apply, re-run with the output ARNs to tighten the policy.
  osis_pipeline_arn = var.osis_pipeline_arn_override != null ? var.osis_pipeline_arn_override : "*"

  eks_oidc_provider_arn    = var.eks_oidc_provider_arn
  eks_namespace            = var.eks_namespace
  eks_service_account_name = var.eks_service_account_name

  tags = local.common_tags
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. OSIS Pipelines
# ─────────────────────────────────────────────────────────────────────────────
module "osis" {
  source = "../modules/osis"

  name_prefix                = local.name_prefix
  opensearch_domain_endpoint = "https://${data.aws_opensearch_domain.dataobs.endpoint}"
  pipeline_role_arn          = module.iam.osis_pipeline_role_arn
  min_units                  = var.osis_min_units
  max_units                  = var.osis_max_units
  log_retention_days         = var.log_retention_days
  amp_remote_write_url       = module.amp.remote_write_url
  enable_amp_metrics_fanout  = var.enable_amp_metrics_fanout

  tags = local.common_tags

  depends_on = [module.iam]
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Amazon Managed Grafana
# ─────────────────────────────────────────────────────────────────────────────
module "amg" {
  source = "../modules/amg"

  name_prefix                = local.name_prefix
  workspace_name             = "${local.name_prefix}-grafana"
  workspace_description      = "DataObs — ${var.environment} observability dashboards"
  grafana_version            = var.grafana_version
  authentication_providers   = var.amg_authentication_providers
  permission_type            = var.amg_permission_type
  workspace_role_arn         = var.amg_permission_type == "CUSTOMER_MANAGED" ? module.iam.amg_role_arn : null
  enable_sns_notifications   = var.amg_enable_sns_notifications
  service_account_token_ttl_seconds = var.amg_token_ttl_seconds

  amp_workspace_url          = module.amp.prometheus_endpoint
  opensearch_domain_endpoint = "https://${data.aws_opensearch_domain.dataobs.endpoint}"
  opensearch_version         = var.opensearch_version

  tags = local.common_tags

  depends_on = [module.amp, module.osis]
}

# ─────────────────────────────────────────────────────────────────────────────
# Post-deploy: tighten OSIS ingest policy with actual pipeline ARNs
# Run: terraform apply -target=module.iam after OSIS pipelines are created.
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_iam_policy" "osis_ingest_scoped" {
  count       = var.osis_pipeline_arn_override == null ? 0 : 0  # managed by iam module first apply
  name        = "${local.name_prefix}-osis-ingest-scoped"
  description = "Tightened OSIS Ingest policy scoped to specific pipeline ARNs"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["osis:Ingest"]
      Resource = [
        module.osis.traces_pipeline_arn,
        module.osis.logs_pipeline_arn,
        module.osis.metrics_pipeline_arn,
      ]
    }]
  })
}
