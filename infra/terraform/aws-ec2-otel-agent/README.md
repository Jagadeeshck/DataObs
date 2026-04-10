# Terraform: EC2 OpenTelemetry Agent rollout via SSM

This Terraform module creates AWS Systems Manager (SSM) documents and associations to install and configure the OTEL/ADOT agent on EC2 instances.

It supports both targeting styles:

1. **Node group (by tag)** using SSM `targets` with `tag:<key>=<value>`.
2. **Individual nodes** using explicit `InstanceIds`.

## What gets created

- `aws_ssm_document` to install `aws-otel-collector`.
- `aws_ssm_document` to write collector config and restart service.
- `aws_ssm_association` for install document.
- `aws_ssm_association` for configure document.

## Prerequisites

- EC2 instances are managed by SSM (SSM Agent + IAM instance profile with `AmazonSSMManagedInstanceCore`).
- Network egress from instances to package source and OTEL gateway.
- A collector config file available locally (for example `config/otel-ec2-agent-config.yaml`).

## Example A: target a node group by tag

```hcl
module "dataobs_ec2_otel_agent" {
  source = "./infra/terraform/aws-ec2-otel-agent"

  aws_region        = "us-east-1"
  agent_config_path = "${path.root}/config/otel-ec2-agent-config.yaml"

  target_type      = "tag"
  target_tag_key   = "Role"
  target_tag_value = "spark-workers"

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
  }
}
```

## Example B: target individual instances

```hcl
module "dataobs_ec2_otel_agent_instances" {
  source = "./infra/terraform/aws-ec2-otel-agent"

  aws_region        = "us-east-1"
  agent_config_path = "${path.root}/config/otel-ec2-agent-config.yaml"

  target_type         = "instance_ids"
  target_instance_ids = ["i-0123456789abcdef0", "i-0123456789abcdef1"]
}
```

## Apply

```bash
terraform init
terraform plan
terraform apply
```

After apply, SSM associations push install + configuration to the selected EC2 targets.
