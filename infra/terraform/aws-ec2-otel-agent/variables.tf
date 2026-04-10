variable "name_prefix" {
  description = "Prefix used for SSM association names."
  type        = string
  default     = "dataobs"
}

variable "aws_region" {
  description = "AWS region where instances run; used in install command."
  type        = string
}

variable "agent_config_path" {
  description = "Path to collector config YAML to be rendered into /etc/otel-agent/config.yaml on EC2."
  type        = string
}

variable "agent_config_destination" {
  description = "Destination path for OTEL agent config on EC2 instance."
  type        = string
  default     = "/etc/otel-agent/config.yaml"
}

variable "agent_service_name" {
  description = "Systemd service name for the OTEL collector agent."
  type        = string
  default     = "aws-otel-collector"
}

variable "install_document_name" {
  description = "Name of the SSM command document used to install the OTEL agent."
  type        = string
  default     = "DataObs-InstallOTELAgent"
}

variable "configure_document_name" {
  description = "Name of the SSM command document used to configure and restart the OTEL agent."
  type        = string
  default     = "DataObs-ConfigureOTELAgent"
}

variable "target_type" {
  description = "How to target EC2 nodes: tag or instance_ids."
  type        = string
  default     = "tag"

  validation {
    condition     = contains(["tag", "instance_ids"], var.target_type)
    error_message = "target_type must be either 'tag' or 'instance_ids'."
  }
}

variable "target_tag_key" {
  description = "Tag key used when target_type=tag."
  type        = string
  default     = "Role"
}

variable "target_tag_value" {
  description = "Tag value used when target_type=tag."
  type        = string
  default     = "data-platform"
}

variable "target_instance_ids" {
  description = "List of EC2 instance IDs used when target_type=instance_ids."
  type        = list(string)
  default     = []

  validation {
    condition     = var.target_type != "instance_ids" || length(var.target_instance_ids) > 0
    error_message = "When target_type is 'instance_ids', provide at least one instance id in target_instance_ids."
  }
}

variable "association_schedule" {
  description = "Optional schedule expression for SSM association. Defaults to rate(30 days)."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to SSM documents."
  type        = map(string)
  default     = {}
}
