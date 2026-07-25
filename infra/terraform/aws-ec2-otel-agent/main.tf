terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  agent_config_b64 = base64encode(file(var.agent_config_path))

  targets = var.target_type == "tag" ? [{ key = "tag:${var.target_tag_key}", values = [var.target_tag_value] }] : [{ key = "InstanceIds", values = var.target_instance_ids }]

  association_schedule = var.association_schedule == null ? "rate(30 days)" : var.association_schedule
}

resource "aws_ssm_document" "otel_agent_install" {
  name            = var.install_document_name
  document_type   = "Command"
  document_format = "JSON"

  content = templatefile("${path.module}/templates/install-agent.json.tftpl", {
    region = var.aws_region
  })

  tags = merge(var.tags, {
    Name = var.install_document_name
  })
}

resource "aws_ssm_document" "otel_agent_configure" {
  name            = var.configure_document_name
  document_type   = "Command"
  document_format = "JSON"

  content = templatefile("${path.module}/templates/configure-agent.json.tftpl", {
    config_b64         = local.agent_config_b64
    config_destination = var.agent_config_destination
    service_name       = var.agent_service_name
  })

  tags = merge(var.tags, {
    Name = var.configure_document_name
  })
}

resource "aws_ssm_association" "install" {
  name             = aws_ssm_document.otel_agent_install.name
  association_name = "${var.name_prefix}-otel-agent-install"
  schedule_expression = local.association_schedule

  dynamic "targets" {
    for_each = local.targets
    content {
      key    = targets.value.key
      values = targets.value.values
    }
  }
}

resource "aws_ssm_association" "configure" {
  name             = aws_ssm_document.otel_agent_configure.name
  association_name = "${var.name_prefix}-otel-agent-configure"
  schedule_expression = local.association_schedule

  dynamic "targets" {
    for_each = local.targets
    content {
      key    = targets.value.key
      values = targets.value.values
    }
  }

  depends_on = [aws_ssm_association.install]
}
