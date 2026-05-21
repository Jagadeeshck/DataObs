# Road Safety Enterprise Demo

## 5-minute flow
1. `./scripts/demo_up.sh`
2. `./scripts/demo_run.sh good`
3. `./scripts/demo_verify.sh`
4. Open all five Kibana dashboards in **Analytics → Dashboards**.
5. `./scripts/demo_run.sh bad`
6. `./scripts/demo_verify.sh`
7. Re-open dashboards and compare deltas.

## Dashboards to open
- `DataObs Road Safety Executive Overview`
- `Data Quality & Bad Data Detection`
- `Freshness / Volume / Schema Drift`
- `Lineage & Impact`
- `Spark Pipeline Performance`

## What each dashboard proves to enterprise buyers
- **DataObs Road Safety Executive Overview**
  - Shows enterprise KPI posture: total runs, good vs bad outcome, records processed, failed checks, alert hotspots, and top affected datasets.
- **Data Quality & Bad Data Detection**
  - Shows concrete control effectiveness: duplicate IDs, null spikes, invalid severity/age ranges, and referential integrity breaks.
- **Freshness / Volume / Schema Drift**
  - Shows reliability governance: freshness SLA breaches, stale datasets, row-count anomalies, and schema drift events.
- **Lineage & Impact**
  - Shows governance and blast radius: source-to-target path, relation type, row count, and downstream impact.
- **Spark Pipeline Performance**
  - Shows platform efficiency: stage duration, throughput, rejected rows, failed stage count, and available executor/driver metrics.

## Good run walkthrough
- Executive: confirm predominantly healthy statuses and expected volume.
- Quality: confirm no severe failures or only low-risk warnings.
- Freshness/Volume/Schema: confirm SLA-compliant freshness and no major drift.
- Lineage: show expected raw→curated relations.
- Spark: show normal stage duration and low reject rates.

## Bad run walkthrough
- Executive: highlight failed checks and impacted datasets.
- Quality: filter `status: fail`, then inspect failed checks per dataset.
- Freshness/Volume/Schema: show stale datasets and anomaly events.
- Lineage: explain which downstream assets become at risk.
- Spark: show slowest/failed stages and throughput degradation.

## Scenario knobs
- `DATAOBS_DEMO_SCENARIO=road_safety`
- `DATAOBS_DEMO_RUN_MODE=good|bad`
- `DATAOBS_DEMO_SCALE=small|medium|large`
- `DATAOBS_POC_FIXTURE_MODE=true`

Large scale is synthetic and generated locally in `/tmp/dataobs/tmp/road_safety`, so 5GB-10GB is opt-in without committing large files.
