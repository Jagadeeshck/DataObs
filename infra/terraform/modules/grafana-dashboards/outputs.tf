# Grafana Dashboards Module — Outputs
# Resolves: https://github.com/Jagadeeshck/DataObs/issues/32

output "folder_uid" {
  description = "UID of the DataObs Grafana folder"
  value       = grafana_folder.dataobs.uid
}

output "dashboard_uids" {
  description = "Map of dashboard name → Grafana UID"
  value       = { for k, v in grafana_dashboard.dataobs : k => v.dashboard_id }
}

output "slack_contact_point_name" {
  description = "Name of the Slack contact point (empty if not configured)"
  value       = length(grafana_contact_point.slack) > 0 ? grafana_contact_point.slack[0].name : ""
}
