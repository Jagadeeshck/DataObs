# DataObs 5-Minute Quick Demo

## 1) Bring up the stack (say: "Elastic Agent/APM is the default telemetry path")
```bash
./scripts/demo_up.sh
```

## 2) Run the pipeline (say: "Fixture mode keeps this demo offline-stable")
```bash
./scripts/demo_run.sh good
```

## 3) Verify output and Kibana dashboard import
```bash
./scripts/demo_verify.sh
```

## What to click in Kibana (exact order)
1. **Analytics → Dashboards**
2. Open **DataObs Road Safety Executive Overview**
3. Open **Data Quality & Bad Data Detection**
4. Open **Freshness / Volume / Schema Drift**
5. Open **Lineage & Impact**
6. Open **Spark Pipeline Performance**

## What each dashboard proves
- **Executive Overview**: run posture, good vs bad status, records processed, failed checks, and alert pressure.
- **Data Quality & Bad Data Detection**: concrete failed checks (duplicates, null spikes, invalid values, referential issues).
- **Freshness / Volume / Schema Drift**: SLA freshness state, stale datasets, row-count anomalies, schema drift evidence.
- **Lineage & Impact**: raw-to-curated flow and downstream blast radius for impacted datasets.
- **Spark Pipeline Performance**: stage latency and throughput (input/output/rejected rows), with failed stages.

## What to show after good run
- In Executive Overview table, show mostly passing status rows and lower failed-check signal.
- In Quality dashboard, show either no failed checks or a low, explainable baseline.
- In Freshness/Volume/Schema dashboard, show expected or in-SLA behavior.

## What to show after bad run
```bash
./scripts/demo_run.sh bad
./scripts/demo_verify.sh
```
- In Executive Overview, show increased failed checks and affected datasets.
- In Quality dashboard, filter `status: fail` and walk through specific failed checks.
- In Freshness/Volume/Schema dashboard, highlight stale/volume/schema anomalies.
- In Lineage dashboard, explain impacted downstream datasets.
- In Spark dashboard, show failed or slow stages.

## Road Safety enterprise POC
See `docs/demo/road-safety-enterprise-demo.md` and run `./scripts/demo_run.sh good|bad [small|medium|large]`.
