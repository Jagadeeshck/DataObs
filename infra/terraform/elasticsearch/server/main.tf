# =============================================================================
# DataObs — Server-Side Elasticsearch (OpenSearch) Cluster
# AWS OpenSearch Service: 3 dedicated masters + 3 hot + 2 warm nodes
# This is the centralised DataObs platform cluster.
# All tenant OTel collectors ship telemetry here.
# =============================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ---------------------------------------------------------------------------
# KMS key for encryption at rest
# ---------------------------------------------------------------------------
resource "aws_kms_key" "dataobs_es" {
  description             = "DataObs Elasticsearch encryption at rest"
  deletion_window_in_days = 14
  enable_key_rotation     = true

  tags = merge(var.common_tags, { Name = "dataobs-es-kms" })
}

resource "aws_kms_alias" "dataobs_es" {
  name          = "alias/dataobs-elasticsearch"
  target_key_id = aws_kms_key.dataobs_es.key_id
}

# ---------------------------------------------------------------------------
# Security group — only allow inbound from OTel collector SG + API SG
# ---------------------------------------------------------------------------
resource "aws_security_group" "dataobs_es" {
  name        = "dataobs-es-server"
  description = "DataObs server-side Elasticsearch: allow HTTPS from collector and API only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTPS from OTel collector"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [var.otel_collector_sg_id]
  }

  ingress {
    description     = "HTTPS from DataObs API"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [var.dataobs_api_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, { Name = "dataobs-es-server-sg" })
}

# ---------------------------------------------------------------------------
# OpenSearch Service domain — server side
# ---------------------------------------------------------------------------
resource "aws_opensearch_domain" "dataobs_server" {
  domain_name    = "dataobs-server"
  engine_version = "OpenSearch_2.11"

  # --- Dedicated master nodes (3 × m6g.large) ---
  cluster_config {
    instance_type            = var.data_node_instance_type
    instance_count           = 3
    dedicated_master_enabled = true
    dedicated_master_type    = var.master_node_instance_type
    dedicated_master_count   = 3
    warm_enabled             = true
    warm_type                = var.warm_node_instance_type
    warm_count               = 2
    zone_awareness_enabled   = true
    zone_awareness_config {
      availability_zone_count = 3
    }
  }

  # --- EBS storage per data node ---
  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = var.data_node_volume_gb
    throughput  = 250
    iops        = 3000
  }

  # --- Encryption at rest using KMS ---
  encrypt_at_rest {
    enabled    = true
    kms_key_id = aws_kms_key.dataobs_es.arn
  }

  # --- TLS in transit ---
  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  # --- Fine-grained access control (FGAC) ---
  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = var.es_master_user
      master_user_password = var.es_master_password
    }
  }

  # --- VPC placement ---
  vpc_options {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.dataobs_es.id]
  }

  # --- Auto-Tune for JVM heap optimisation ---
  auto_tune_options {
    desired_state = "ENABLED"
    rollback_on_disable = "NO_ROLLBACK"

    maintenance_schedule {
      start_at = timeadd(timestamp(), "24h")
      duration {
        value = 2
        unit  = "HOURS"
      }
      cron_expression_for_recurrence = "cron(0 2 ? * SUN *)"
    }
  }

  # --- Snapshot to S3 ---
  snapshot_options {
    automated_snapshot_start_hour = 3
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.dataobs_es_slow.arn
    log_type                 = "INDEX_SLOW_LOGS"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.dataobs_es_app.arn
    log_type                 = "ES_APPLICATION_LOGS"
  }

  tags = merge(var.common_tags, { Name = "dataobs-server" })
}

# ---------------------------------------------------------------------------
# Access policy — deny everything except the specified IAM roles
# ---------------------------------------------------------------------------
resource "aws_opensearch_domain_policy" "dataobs_server" {
  domain_name = aws_opensearch_domain.dataobs_server.domain_name

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { AWS = var.allowed_iam_role_arns }
        Action    = "es:*"
        Resource  = "${aws_opensearch_domain.dataobs_server.arn}/*"
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# S3 bucket for manual + automated snapshots
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "dataobs_es_snapshots" {
  bucket = "dataobs-es-snapshots-${data.aws_caller_identity.current.account_id}"
  tags   = merge(var.common_tags, { Name = "dataobs-es-snapshots" })
}

resource "aws_s3_bucket_versioning" "dataobs_es_snapshots" {
  bucket = aws_s3_bucket.dataobs_es_snapshots.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "dataobs_es_snapshots" {
  bucket = aws_s3_bucket.dataobs_es_snapshots.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.dataobs_es.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "dataobs_es_snapshots" {
  bucket                  = aws_s3_bucket.dataobs_es_snapshots.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------------------
# CloudWatch log groups for ES logs
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "dataobs_es_slow" {
  name              = "/dataobs/elasticsearch/slow-logs"
  retention_in_days = 30
  tags              = var.common_tags
}

resource "aws_cloudwatch_log_group" "dataobs_es_app" {
  name              = "/dataobs/elasticsearch/app-logs"
  retention_in_days = 30
  tags              = var.common_tags
}

# ---------------------------------------------------------------------------
# CloudWatch alarms — cluster health guardrails
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "es_cluster_red" {
  alarm_name          = "dataobs-es-cluster-red"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ClusterStatus.red"
  namespace           = "AWS/ES"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "DataObs ES cluster status is RED"
  alarm_actions       = var.alarm_sns_arns
  dimensions = {
    DomainName = aws_opensearch_domain.dataobs_server.domain_name
    ClientId   = data.aws_caller_identity.current.account_id
  }
  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "es_jvm_heap" {
  alarm_name          = "dataobs-es-jvm-heap-high"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 3
  metric_name         = "JVMMemoryPressure"
  namespace           = "AWS/ES"
  period              = 300
  statistic           = "Maximum"
  threshold           = 85
  alarm_description   = "DataObs ES JVM heap pressure >= 85% for 15 minutes"
  alarm_actions       = var.alarm_sns_arns
  dimensions = {
    DomainName = aws_opensearch_domain.dataobs_server.domain_name
    ClientId   = data.aws_caller_identity.current.account_id
  }
  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "es_free_storage" {
  alarm_name          = "dataobs-es-free-storage-low"
  comparison_operator = "LessThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/ES"
  period              = 300
  statistic           = "Minimum"
  threshold           = 20480 # 20 GB in MiB
  alarm_description   = "DataObs ES free storage < 20GB on any node"
  alarm_actions       = var.alarm_sns_arns
  dimensions = {
    DomainName = aws_opensearch_domain.dataobs_server.domain_name
    ClientId   = data.aws_caller_identity.current.account_id
  }
  tags = var.common_tags
}
