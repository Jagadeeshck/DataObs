variable "name_prefix" {
  description = "Prefix for resource names (e.g. 'dataobs-prod')."
  type        = string
  default     = "dataobs"
}

variable "workspace_alias" {
  description = "Human-readable alias for the AMP workspace."
  type        = string
  default     = "dataobs-metrics"
}

variable "enable_logging" {
  description = "Create a CloudWatch log group and enable AMP logging."
  type        = bool
  default     = true
}

variable "log_group_arn" {
  description = "ARN of an existing CloudWatch log group to use for AMP logging. If null and enable_logging=true, a new log group is created."
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "Retention period in days for the AMP log group."
  type        = number
  default     = 90
}

variable "alarm_ingestion_error_threshold" {
  description = "Number of ingestion errors per 5 min before triggering the CloudWatch alarm."
  type        = number
  default     = 5
}

variable "alarm_sns_topic_arn" {
  description = "ARN of the SNS topic to notify on AMP alarms. Set to null to disable."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to all AMP resources."
  type        = map(string)
  default     = {}
}
