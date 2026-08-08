# Operating Elastic Cases integration

Set `DATAOBS_ELASTIC_CASES_ENABLED=true`, configure an HTTPS Kibana base URL, a Case-runtime API key in the environment/secret store, and `DATAOBS_KIBANA_SPACES` as comma-separated `environment=space` mappings. The default is disabled. Grant only Case read/write privileges. A timeout after create is an uncertain outcome: reconcile by the deterministic tag; do not repeat creation. Provider outage does not block incident ingestion.
# Durable runtime

Production composition must use `ElasticsearchCaseRepository`. Case creation reserves the deterministic scoped link
before Kibana is contacted. A timeout after submission is retained as `create_reconciliation_required`; operators
must reconcile by the exact `dataobs-ref-*` tag and must never retry creation based on a timeout or title similarity.
