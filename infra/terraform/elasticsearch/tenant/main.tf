# =============================================================================
# DataObs — Tenant-Side Elasticsearch (OpenSearch) Cluster
# Single-AZ lightweight OpenSearch domain per tenant.
# Receives data via Cross-Cluster Replication (CCR) from the server cluster
# for tenant-scoped lineage and quality results.
# Tenants can also query this directly from their own VPC.
# =============================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    elasticsearch = {
      source  = "phillbaker/elasticsearch"
      version = "~> 2.0"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  tenant_domain_name = "dataobs-tenant-${var.tenant_id}"
}

# ---------------------------------------------------------------------------
# KMS key for this tenant's encryption at rest
# ---------------------------------------------------------------------------
resource "aws_kms_key" "tenant_es" {
  description             = "DataObs tenant ${var.tenant_id} Elasticsearch encryption"
  deletion_window_in_days = 14
  enable_key_rotation     = true
  tags                    = merge(var.common_tags, { tenant_id = var.tenant_id })
}

# ---------------------------------------------------------------------------
# Security group — allow HTTPS from tenant VPC CIDR only
# ---------------------------------------------------------------------------
resource "aws_security_group" "tenant_es" {
  name        = "dataobs-es-tenant-${var.tenant_id}"
  description = "DataObs tenant ${var.tenant_id} Elasticsearch: HTTPS from tenant VPC only"
  vpc_id      = var.tenant_vpc_id

  ingress {
    description = "HTTPS from tenant VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.tenant_vpc_cidr]
  }

  # Allow CCR replication pull from server cluster (via VPC peering or PrivateLink)
  ingress {
    description     = "CCR replication from server cluster"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [var.server_es_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, { Name = "dataobs-es-tenant-${var.tenant_id}-sg", tenant_id = var.tenant_id })
}

# ---------------------------------------------------------------------------
# Tenant OpenSearch domain
# t3.medium.search — single AZ, single node (lightweight per-tenant shard)
# ---------------------------------------------------------------------------
resource "aws_opensearch_domain" "tenant" {
  domain_name    = local.tenant_domain_name
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type          = var.tenant_node_instance_type
    instance_count         = 1
    zone_awareness_enabled = false
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = var.tenant_volume_gb
  }

  encrypt_at_rest {
    enabled    = true
    kms_key_id = aws_kms_key.tenant_es.arn
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  # Fine-grained access control — tenant master user
  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = var.tenant_es_master_user
      master_user_password = var.tenant_es_master_password
    }
  }

  vpc_options {
    subnet_ids         = [var.tenant_subnet_id]
    security_group_ids = [aws_security_group.tenant_es.id]
  }

  snapshot_options {
    automated_snapshot_start_hour = 4
  }

  tags = merge(var.common_tags, {
    Name      = local.tenant_domain_name
    tenant_id = var.tenant_id
  })
}

# ---------------------------------------------------------------------------
# Access policy for tenant domain
# ---------------------------------------------------------------------------
resource "aws_opensearch_domain_policy" "tenant" {
  domain_name = aws_opensearch_domain.tenant.domain_name

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { AWS = var.tenant_allowed_role_arns }
        Action    = "es:*"
        Resource  = "${aws_opensearch_domain.tenant.arn}/*"
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# Secrets Manager: store tenant API key for OTel collector auth
# ---------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "tenant_es_api_key" {
  name        = "dataobs/tenants/${var.tenant_id}/es-api-key"
  description = "DataObs tenant ${var.tenant_id} Elasticsearch API key for OTel collector"
  kms_key_id  = aws_kms_key.tenant_es.arn
  tags        = merge(var.common_tags, { tenant_id = var.tenant_id })
}

resource "aws_secretsmanager_secret_version" "tenant_es_api_key" {
  secret_id = aws_secretsmanager_secret.tenant_es_api_key.id
  secret_string = jsonencode({
    tenant_id       = var.tenant_id
    endpoint        = "https://${aws_opensearch_domain.tenant.endpoint}"
    api_key         = var.tenant_es_api_key
    server_endpoint = var.server_es_endpoint
  })
}
