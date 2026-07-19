# Repository generated-artifact policy

DataObs commits source inputs and reproducibility metadata, not installed dependencies or build output. JavaScript
lockfiles (including `pnpm-lock.yaml`) are source inputs and **must** remain tracked. The following are never committed:

- `node_modules` directories;
- Playwright browser caches, reports, screenshots, traces, and test-results directories;
- coverage output;
- Vite caches and Console `dist` output; and
- browser binaries or package-manager stores.

The root `.gitignore` applies these rules throughout the repository. Run
`python scripts/check_generated_artifacts.py` before committing; CI runs the same command from a clean checkout and
fails with the complete tracked-path list. Recreate Console dependencies and output with:

```bash
cd ui/dataobs-console
corepack enable
pnpm install --frozen-lockfile
pnpm test
pnpm build
```

Removal is safe only for output reproducible by a documented command. Configuration, fixtures, lockfiles, generated
API contracts used for drift detection, and human-authored test evidence are not removed merely because a tool reads
them. CI diagnostics must be redacted before upload and must never contain Kafka payloads, credentials, or browser
binaries.
