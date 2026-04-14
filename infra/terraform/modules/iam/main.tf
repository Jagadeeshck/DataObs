# =============================================================================
# DataObs — IAM Module
# =============================================================================
# Creates all IAM roles and policies needed for the DataObs AWS backend:
#
#   1. OTel Collector role  — used by EC2 / ECS / EKS workloads running the
#      collector; needs AMP RemoteWrite + OSIS Ingest permissions.
#   2. OSIS pipeline role   — assumed by the OSIS service principal; needs
#      es:ESHttp* on the target OpenSearch domain.
#   3. AMG workspace role   — assumed by the AMG service; needs
#      AMP query + CloudWatch read + X-Ray read permissions.
# =============================================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. OTel Collector IAM Role
# ─────────────────────────────────────────────────────────────────────────────
data "aws_iam_policy_document" "collector_assume" {
  # EC2 instances
  statement {
    sid     = "AllowEC2Assume"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }

  # ECS task execution
  statement {
    sid     = "AllowECSAssume"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }

  # EKS workloads via IRSA (annotated service account → OIDC provider)
  dynamic "statement" {
    for_each = var.eks_oidc_provider_arn != null ? [1] : []
    content {
      sid     = "AllowEKSIRSAAssume"
      actions = ["sts:AssumeRoleWithWebIdentity"]
      principals {
        type        = "Federated"
        identifiers = [var.eks_oidc_provider_arn]
      }
      condition {
        test     = "StringEquals"
        variable = "${replace(var.eks_oidc_provider_arn, "arn:aws:iam::${local.account_id}:oidc-provider/", "")}:sub"
        values   = ["system:serviceaccount:${var.eks_namespace}:${var.eks_service_account_name}"]
      }
    }
  }
}

resource "aws_iam_role" "collector" {
  name                 = "${var.name_prefix}-otel-collector"
  description          = "DataObs OTel Collector — AMP RemoteWrite + OSIS Ingest"
  assume_role_policy   = data.aws_iam_policy_document.collector_assume.json
  max_session_duration = 3600

  tags = merge(var.tags, { Name = "${var.name_prefix}-otel-collector" })
}

resource "aws_iam_instance_profile" "collector" {
  name = "${var.name_prefix}-otel-collector"
  role = aws_iam_role.collector.name
  tags = var.tags
}

# ── AMP RemoteWrite ──────────────────────────────────────────────────────────
data "aws_iam_policy_document" "amp_write" {
  statement {
    sid       = "AMPRemoteWrite"
    actions   = ["aps:RemoteWrite", "aps:GetSeries", "aps:GetLabels", "aps:GetMetricMetadata"]
    resources = [var.amp_workspace_arn]
  }
}

resource "aws_iam_policy" "amp_write" {
  name        = "${var.name_prefix}-amp-remote-write"
  description = "Allows the OTel Collector to write metrics to AMP workspace"
  policy      = data.aws_iam_policy_document.amp_write.json
  tags        = var.tags
}

resource "aws_iam_role_policy_attachment" "collector_amp" {
  role       = aws_iam_role.collector.name
  policy_arn = aws_iam_policy.amp_write.arn
}

# ── OSIS Ingest ──────────────────────────────────────────────────────────────
data "aws_iam_policy_document" "osis_ingest" {
  statement {
    sid       = "OSISIngest"
    actions   = ["osis:Ingest"]
    resources = [var.osis_pipeline_arn]
  }
}

resource "aws_iam_policy" "osis_ingest" {
  name        = "${var.name_prefix}-osis-ingest"
  description = "Allows the OTel Collector to push OTLP data to OSIS pipeline"
  policy      = data.aws_iam_policy_document.osis_ingest.json
  tags        = var.tags
}

resource "aws_iam_role_policy_attachment" "collector_osis" {
  role       = aws_iam_role.collector.name
  policy_arn = aws_iam_policy.osis_ingest.arn
}

# ── CloudWatch read (for awscloudwatch receiver) ─────────────────────────────
resource "aws_iam_role_policy_attachment" "collector_cloudwatch" {
  role       = aws_iam_role.collector.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess"
}

# ── X-Ray write (for awsxray receiver forwarding) ────────────────────────────
resource "aws_iam_role_policy_attachment" "collector_xray" {
  role       = aws_iam_role.collector.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# ── EC2 SSM core (for SSM-managed OTel installs) ────────────────────────────
resource "aws_iam_role_policy_attachment" "collector_ssm" {
  role       = aws_iam_role.collector.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. OSIS Pipeline Role
# ─────────────────────────────────────────────────────────────────────────────
data "aws_iam_policy_document" "osis_assume" {
  statement {
    sid     = "AllowOSISAssume"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["osis-pipelines.amazonaws.com"]
    }
    # Prevent confused deputy: only our own pipeline can assume this role
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "osis_pipeline" {
  name               = "${var.name_prefix}-osis-pipeline"
  description        = "DataObs OSIS pipeline — writes traces/logs/metrics to OpenSearch"
  assume_role_policy = data.aws_iam_policy_document.osis_assume.json

  tags = merge(var.tags, { Name = "${var.name_prefix}-osis-pipeline" })
}

# ── OpenSearch index write permissions ───────────────────────────────────────
data "aws_iam_policy_document" "osis_os_write" {
  statement {
    sid     = "OpenSearchDescribe"
    actions = ["es:DescribeDomain"]
    resources = [
      "arn:aws:es:${local.region}:${local.account_id}:domain/*"
    ]
  }

  statement {
    sid     = "OpenSearchWrite"
    actions = ["es:ESHttp*"]
    resources = [
      "${var.opensearch_domain_arn}/*"
    ]
  }

  # Required for OSIS to publish pipeline metrics
  statement {
    sid     = "CloudWatchMetrics"
    actions = ["cloudwatch:PutMetricData"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["AWS/OSIS"]
    }
  }

  # Required for OSIS to write pipeline logs
  statement {
    sid = "CloudWatchLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogDelivery",
      "logs:PutLogEvents",
      "logs:PutRetentionPolicy",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
    ]
    resources = [
      "arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/vendedlogs/OpenSearchIngestion/${var.name_prefix}-*",
      "arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/vendedlogs/OpenSearchIngestion/${var.name_prefix}-*:*",
    ]
  }

  # AMP fan-out from OSIS metrics pipeline
  dynamic "statement" {
    for_each = var.amp_workspace_arn != null ? [1] : []
    content {
      sid     = "AMPRemoteWriteFromOSIS"
      actions = ["aps:RemoteWrite"]
      resources = [var.amp_workspace_arn]
    }
  }
}

resource "aws_iam_policy" "osis_os_write" {
  name        = "${var.name_prefix}-osis-opensearch-write"
  description = "Allows OSIS pipeline to write to OpenSearch domain and publish logs/metrics"
  policy      = data.aws_iam_policy_document.osis_os_write.json
  tags        = var.tags
}

resource "aws_iam_role_policy_attachment" "osis_pipeline_write" {
  role       = aws_iam_role.osis_pipeline.name
  policy_arn = aws_iam_policy.osis_os_write.arn
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. Amazon Managed Grafana (AMG) Workspace Role
# ─────────────────────────────────────────────────────────────────────────────
data "aws_iam_policy_document" "amg_assume" {
  statement {
    sid     = "AllowAMGAssume"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["grafana.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "amg" {
  name               = "${var.name_prefix}-amg-workspace"
  description        = "DataObs Amazon Managed Grafana — AMP query + OpenSearch + CloudWatch + X-Ray"
  assume_role_policy = data.aws_iam_policy_document.amg_assume.json

  tags = merge(var.tags, { Name = "${var.name_prefix}-amg-workspace" })
}

# ── AMP query permissions ────────────────────────────────────────────────────
data "aws_iam_policy_document" "amg_permissions" {
  statement {
    sid = "AMPQuery"
    actions = [
      "aps:QueryMetrics",
      "aps:GetSeries",
      "aps:GetLabels",
      "aps:GetMetricMetadata",
      "aps:ListWorkspaces",
      "aps:DescribeWorkspace",
    ]
    resources = [var.amp_workspace_arn]
  }

  statement {
    sid = "OpenSearchQuery"
    actions = [
      "es:ESHttpGet",
      "es:ESHttpPost",
      "es:ESHttpHead",
      "es:DescribeDomain",
      "es:ListDomainNames",
    ]
    resources = [
      "${var.opensearch_domain_arn}/*",
      var.opensearch_domain_arn,
    ]
  }

  statement {
    sid = "CloudWatchRead"
    actions = [
      "cloudwatch:DescribeAlarmsForMetric",
      "cloudwatch:DescribeAlarmHistory",
      "cloudwatch:DescribeAlarms",
      "cloudwatch:ListMetrics",
      "cloudwatch:GetMetricStatistics",
      "cloudwatch:GetMetricData",
      "cloudwatch:GetInsightRuleReport",
    ]
    resources = ["*"]
  }

  statement {
    sid = "XRayRead"
    actions = [
      "xray:BatchGetTraces",
      "xray:GetTraceSummaries",
      "xray:GetTraceGraph",
      "xray:GetGroups",
      "xray:GetGroupSummaries",
      "xray:GetTimeSeriesServiceStatistics",
      "xray:ListTagsForResource",
      "xray:GetInsight",
      "xray:GetInsightSummaries",
      "xray:GetInsightImpactGraph",
      "xray:GetInsightEvents",
    ]
    resources = ["*"]
  }

  statement {
    sid = "SNSForAlerting"
    actions = [
      "sns:Publish",
      "sns:ListTopics",
    ]
    resources = ["arn:aws:sns:${local.region}:${local.account_id}:dataobs-*"]
  }

  # Secrets Manager — allows AMG to read data source credentials
  statement {
    sid = "SecretsManager"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:ListSecrets",
    ]
    resources = ["arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:dataobs/*"]
  }
}

resource "aws_iam_policy" "amg_permissions" {
  name        = "${var.name_prefix}-amg-permissions"
  description = "DataObs AMG workspace — AMP query, OpenSearch read, CloudWatch, X-Ray, SNS"
  policy      = data.aws_iam_policy_document.amg_permissions.json
  tags        = var.tags
}

resource "aws_iam_role_policy_attachment" "amg" {
  role       = aws_iam_role.amg.name
  policy_arn = aws_iam_policy.amg_permissions.arn
}
