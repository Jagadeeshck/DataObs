# DataObs 5-Minute Quick Demo

## 1) Bring up the stack (say: "Elastic Agent/APM is the default telemetry path")
```bash
./scripts/demo_up.sh
```

## 2) Run the pipeline (say: "Fixture mode keeps this demo offline-stable")
```bash
./scripts/demo_run.sh
```

## 3) Verify output
```bash
./scripts/demo_verify.sh
```

## What to click in Kibana
1. **Observability → APM → Services**
   - Show `dataobs-poc-pipeline`.
   - Open a trace and explain ingest/transform/lineage stages.
2. **Analytics → Discover**
   - Open `dataobs-quality` and `dataobs-lineage`.
   - Filter by latest `run_id`.
3. **Analytics → Dashboards**
   - `[DataObs POC] Pipeline Health`
   - `[DataObs POC] Data Quality Overview`

## What to say
- "This POC defaults to Elastic Agent-managed APM, not a standalone collector."
- "The otel-collector remains available only with `--profile otel`."
- "For demo reliability, fixture mode uses local sample datasets under `fixtures/poc/`."
