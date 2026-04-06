# DataObs Operations Wiki

## What operators do daily
- Check failed quality/freshness jobs.
- Review top anomalies from Elasticsearch ML.
- Triage critical incidents pushed to ServiceNow.
- Validate that OTEL ingest latency remains within SLA.

## Standard runbooks
1. **Freshness breach**
   - Verify source job status.
   - Check late-arriving partition data.
   - Correlate with upstream pipeline retries.

2. **Schema drift**
   - Identify breaking column changes.
   - Run impact analysis in lineage graph.
   - Trigger producer contract workflow.

3. **High anomaly score (ML)**
   - Inspect anomaly timeline and influencer fields.
   - Confirm whether traffic/seasonality explains spike.
   - Create/update suppression rule if false positive.

## Weekly governance review
- Data contract compliance by domain.
- Incident MTTR and recurrence trends.
- Model precision/recall review for ML alerts.
- Cost review for index retention and collector throughput.
