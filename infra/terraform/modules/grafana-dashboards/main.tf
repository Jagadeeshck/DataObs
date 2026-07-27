# Grafana Dashboards Terraform Module
# Provisions dashboards, folders, alert rules, and contact points.
#
# Resolves: https://github.com/Jagadeeshck/DataObs/issues/32

terraform {
  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = ">= 3.0"
    }
  }
}

provider "grafana" {
  url  = var.grafana_url
  auth = var.grafana_auth
}

# ── Folder ────────────────────────────────────────────────────────────────────
resource "grafana_folder" "dataobs" {
  title = var.folder_title
}

# ── Dashboards ────────────────────────────────────────────────────────────────
locals {
  dashboards = {
    "dataobs-overview"     = file("${path.module}/dashboards/dataobs-overview.json")
    "quality-checks"       = file("${path.module}/dashboards/quality-checks.json")
    "otel-pipeline-health" = file("${path.module}/dashboards/otel-pipeline-health.json")
    "alert-delivery"       = file("${path.module}/dashboards/alert-delivery.json")
  }
}

resource "grafana_dashboard" "dataobs" {
  for_each    = local.dashboards
  folder      = grafana_folder.dataobs.id
  config_json = each.value
}

# ── Contact Points ────────────────────────────────────────────────────────────
resource "grafana_contact_point" "slack" {
  count = var.alert_slack_webhook_url != "" ? 1 : 0
  name  = "dataobs-slack"

  slack {
    url   = var.alert_slack_webhook_url
    title = "DataObs Alert — {{ .CommonLabels.alertname }}"
    text  = "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}"
  }
}

resource "grafana_contact_point" "pagerduty" {
  count = var.alert_pagerduty_integration_key != "" ? 1 : 0
  name  = "dataobs-pagerduty"

  pagerduty {
    integration_key = var.alert_pagerduty_integration_key
    severity        = "critical"
  }
}

# ── Alert Rule — Quality check failure ────────────────────────────────────────
resource "grafana_rule_group" "quality_checks" {
  name             = "dataobs-quality-checks"
  folder_uid       = grafana_folder.dataobs.uid
  interval_seconds = 60

  rule {
    name      = "Quality Check Failure Rate High"
    condition = "C"

    data {
      ref_id         = "A"
      datasource_uid = var.datasource_prometheus_uid
      model = jsonencode({
        expr          = "rate(dataobs_quality_check_failed_total[5m])"
        instant       = false
        intervalMs    = 1000
        maxDataPoints = 43200
        refId         = "A"
      })
      relative_time_range {
        from = 300
        to   = 0
      }
    }

    data {
      ref_id         = "C"
      datasource_uid = "__expr__"
      model = jsonencode({
        conditions = [{
          evaluator = { params = [0.1], type = "gt" }
          operator  = { type = "and" }
          query     = { params = ["A"] }
          reducer   = { type = "avg" }
          type      = "query"
        }]
        refId = "C"
        type  = "classic_conditions"
      })
      relative_time_range {
        from = 300
        to   = 0
      }
    }

    annotations = {
      summary     = "Quality check failure rate exceeds 10%/min in {{ $labels.table }}"
      description = "DataObs detected elevated quality check failure rate. Check the Quality Checks dashboard."
    }

    labels = {
      severity    = "critical"
      environment = var.environment
    }

    no_data_state  = "OK"
    exec_err_state = "Error"

    for = "5m"

    notification_settings {
      contact_point = length(grafana_contact_point.slack) > 0 ? grafana_contact_point.slack[0].name : "grafana-default-email"
    }
  }
}
