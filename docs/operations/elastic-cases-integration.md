# Operating Elastic Cases integration

Set `DATAOBS_ELASTIC_CASES_ENABLED=true`, configure an HTTPS Kibana base URL, a Case-runtime API key in the environment/secret store, and `DATAOBS_KIBANA_SPACES` as comma-separated `environment=space` mappings. The default is disabled. Grant only Case read/write privileges. A timeout after create is an uncertain outcome: reconcile by the deterministic tag; do not repeat creation. Provider outage does not block incident ingestion.
