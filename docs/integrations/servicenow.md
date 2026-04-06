# ServiceNow Integration

DataObs can create incidents automatically when critical data quality or freshness rules fail.

## Integration flow
1. DataObs check fails (e.g., freshness SLA breach).
2. Alert manager maps severity to ServiceNow priority.
3. DataObs posts incident payload into ServiceNow table API.
4. Incident number is attached back to DataObs event timeline.

## Required configuration

```yaml
alerting:
  channels:
    servicenow:
      enabled: true
      instance_url: "https://<your-instance>.service-now.com"
      username: "${SERVICENOW_USER}"
      password: "${SERVICENOW_PASSWORD}"
      severity_mapping:
        critical: "1"
        high: "2"
        medium: "3"
        low: "4"
```

## Recommended incident fields
- `short_description`: one-line issue summary
- `description`: full context including affected dataset and runbook URL
- `priority`: mapped from DataObs severity
- custom fields:
  - `u_dataobs_source`
  - `u_dataobs_severity`

## Operational tips
- Start with `critical` and `high` only.
- Route by assignment group per domain (data platform, BI, ML).
- Add runbook links in incident description for faster triage.
