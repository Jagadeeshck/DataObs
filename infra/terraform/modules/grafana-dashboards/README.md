# Grafana Dashboards Terraform Module

Provisions DataObs Grafana dashboards, folders, alert rules, and
contact points as code. Works with both Grafana Cloud and AWS AMG.

## Usage

```hcl
module "grafana_dashboards" {
  source = "./infra/terraform/modules/grafana-dashboards"

  grafana_url                     = "https://my-workspace.grafana.net"
  grafana_auth                    = var.grafana_api_key
  datasource_prometheus_uid       = "prometheus-amp"
  environment                     = "production"
  alert_slack_webhook_url         = var.slack_webhook
  alert_pagerduty_integration_key = var.pagerduty_key
}
```

## Resources Provisioned

| Resource | Description |
|----------|-------------|
| `grafana_folder` | DataObs folder |
| `grafana_dashboard` | 4 dashboards |
| `grafana_contact_point` | Slack + PagerDuty |
| `grafana_rule_group` | Quality check failure alert |

Resolves: [#32](https://github.com/Jagadeeshck/DataObs/issues/32)
