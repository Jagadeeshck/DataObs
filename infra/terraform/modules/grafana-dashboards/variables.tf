# Grafana Dashboards Terraform Module — Variables
# Resolves: https://github.com/Jagadeeshck/DataObs/issues/32

variable "grafana_url" {
  type        = string
  description = "Grafana workspace URL (Grafana Cloud or AMG endpoint)"
}

variable "grafana_auth" {
  type        = string
  sensitive   = true
  description = "Grafana API key or service account token"
}

variable "folder_title" {
  type        = string
  default     = "DataObs"
  description = "Grafana folder name for all DataObs dashboards"
}

variable "datasource_prometheus_uid" {
  type        = string
  description = "UID of the Prometheus/AMP data source in Grafana"
}

variable "datasource_elasticsearch_uid" {
  type        = string
  default     = ""
  description = "UID of the Elasticsearch data source in Grafana (optional)"
}

variable "environment" {
  type        = string
  description = "Deployment environment tag (e.g. production)"
}

variable "alert_slack_webhook_url" {
  type        = string
  sensitive   = true
  default     = ""
  description = "Slack webhook URL for Grafana alert notifications"
}

variable "alert_pagerduty_integration_key" {
  type        = string
  sensitive   = true
  default     = ""
  description = "PagerDuty Events API v2 integration key"
}
