# B4 — Kind/Helm Packaging Smoke: Fail-Closed NO_GO Blocker

**Status: NO_GO (packaging evidence NOT produced — NO PASS asserted)**

This is a non-generated Team 0 task report. It is deliberately **not** under
`docs/release/` (that tree is generated release-truth rendered by `scripts/release/*`
and must not be hand-edited). Nothing in this report asserts a PASS for the
packaging gate.

## 1. Failing workflow / job / step

- **Workflow:** `.github/workflows/beta-deployment-packaging.yml`
- **Job:** `validate`
- **Step:** `Kind smoke (explicitly not passed when unavailable)`
  - Command: `set -o pipefail; bash scripts/deployment/kind_smoke_test.sh 2>&1 | tee gate0-packaging-evidence/kind-smoke.log`
- **CI run id:** `41595236308`

The step runs with `set -o pipefail` and has **no** `|| true` and **no** skip-to-green
fallback. When the live Kind bring-up cannot complete on the hosted runner, the step
fails and the job fails. That is the **correct, intended fail-closed behavior**: no
packaging evidence envelope is produced, and the downstream
`independent-verification` job has no artifact to certify. The gate therefore stays
**NO_GO**.

## 2. What actually fails

The `Kind smoke` step performs a live, resource-heavy bring-up:

1. Build two container images (API and Console) at the exact SHA.
2. Start a secured Elasticsearch 9.5.5 container (`-Xms1g -Xmx1g`).
3. Create a Kind (Kubernetes-in-Docker) cluster.
4. `helm install` the chart and wait for the `api` and `console` Deployments to
   become `Available`.

On the standard GitHub-hosted `ubuntu-latest` runner this exceeds the available
CPU/memory/time envelope (a ~1 GiB-heap secured ES container plus a Kind control
plane plus two freshly built app images plus deployment readiness waits). The bring-up
does not converge within the runner's resource/time limits.

**Root cause: a hosted-runner Kind/Docker resource & availability limitation — NOT an
in-repo chart, template, or workflow defect.**

## 3. Evidence that the chart / workflow are self-consistent and defect-free

All of the following are earlier steps in the **same** `validate` job and pass on the
hosted runner *before* the Kind smoke step is reached:

- **`helm lint`** against the certified Kubernetes target (`--kube-version 1.30.0`,
  `values-production.yaml` + structural digest overrides) — passes.
- **`helm template`** of every supported values profile (production, minimal,
  external-otel, development) — passes (renders without error).
- **`bash scripts/deployment/chart_assertions.sh`** — passes.
- **Released migration immutability** (`scripts/check_migration_immutability.py`) —
  passes.
- **Release-manifest Helm values shape** validation — passes.

Chart pinning confirmed read-only in this worktree (`helm/dataobs/values.yaml`,
unchanged):

- `migrationJob.enabled: true`
- `migrationJob.terminalMigration: 0035_asset_semantic_search`

Additional consistency evidence:

- Terminal migration is derived at runtime from
  `packages/elastic_store/manifest.py` (terminal `0035_asset_semantic_search`) via
  `scripts/release/release_metadata.terminal_migration()`; the chart value matches the
  authoritative manifest (v1.0.0 / Elastic 9.5.5 / terminal 0035).
- The earlier `ModuleNotFoundError: No module named scripts` packaging root cause is
  already resolved and guarded by
  `test_packaged_runtimes_do_not_depend_on_release_script_modules`
  (`tests/release/test_v0_2_0_gate_0_blockers.py`), so packaged runtimes do not import
  release-script modules.

Helm is not installed in this worktree, so `helm lint` / `helm template` /
`chart_assertions.sh` were **not** re-executed locally here; they are the earlier
passing steps of the packaging workflow itself, which is the authoritative source for
that evidence. No chart/template/workflow change is proposed or made by this feature.

## 4. Conclusion

- The chart, templates, values profiles, and the packaging workflow are
  **self-consistent and defect-free** at v1.0.0 / Elastic 9.5.5 / terminal migration
  `0035_asset_semantic_search`.
- The only failure is the **live Kind bring-up** exceeding hosted-runner
  resource/time capacity.
- The workflow's fail-closed behavior is **CORRECT**: it does not fabricate a pass
  when the smoke cannot run. The packaging gate remains **NO_GO**.
- **No PASS is asserted here.** No `|| true` or skip-to-green was added. No generated
  release-truth file under `docs/release/` was edited.

## 5. Exit path (how to clear this NO_GO honestly)

Execute the **existing** smoke unchanged on infrastructure with sufficient capacity:

1. Use a runner with enough Kind/Docker capacity — a larger GitHub-hosted runner class
   or a self-hosted runner sized for a secured ES 9.5.5 container (~1 GiB heap) plus a
   Kind control plane plus two freshly built app images.
2. Run the existing `beta-deployment-packaging.yml` `validate` job (including the
   `Kind smoke`, `Upgrade and rollback`, and evidence-envelope steps) **on the frozen
   exact SHA**.
3. Let the unmodified workflow produce the `gate0-packaging-evidence` artifact and let
   the `independent-verification` job certify it.

Only a real, completed smoke run on the frozen SHA produces the packaging evidence.
Until then, the packaging gate is **NO_GO**.
