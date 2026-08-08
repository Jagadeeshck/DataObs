# Running a data change gate in CI

Run `python -m services.change_gates.cli evaluate --project PROJECT --base-manifest base/manifest.json --head-manifest target/manifest.json --run-results target/run_results.json --format json`. Add aggregate profiles with `--baseline-profile` and `--profile`; raw rows are prohibited. Markdown output can be written to `$GITHUB_STEP_SUMMARY` without granting DataObs a source-control token.

Exit codes are: 0 passed or advisory warning; 1 enforced failure; 2 evaluation/system error; 3 partial because required evidence is missing. The CLI never merges, approves, comments, pushes, or deploys.
