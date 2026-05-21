# Road Safety Enterprise Demo

## 5-minute flow
1. `./scripts/demo_up.sh`
2. `./scripts/demo_run.sh good`
3. `./scripts/demo_verify.sh`
4. `./scripts/demo_run.sh bad`
5. `./scripts/demo_verify.sh`

## 15-minute flow
- Run `good medium`, review `dataobs-rs-*` curated outputs.
- Run `bad medium`, compare failed checks in `dataobs-quality` and alerts in `dataobs-alerts`.
- Review `dataobs-spark-metrics` for stage duration/input-output/rejected counts.

## Scenario knobs
- `DATAOBS_DEMO_SCENARIO=road_safety`
- `DATAOBS_DEMO_RUN_MODE=good|bad`
- `DATAOBS_DEMO_SCALE=small|medium|large`
- `DATAOBS_POC_FIXTURE_MODE=true`

Large scale is synthetic and generated locally in `/tmp/dataobs/tmp/road_safety`, so 5GB-10GB is opt-in without committing large files.
