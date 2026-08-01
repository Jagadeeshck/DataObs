# Contributing to DataObs

Thank you for considering a contribution to DataObs. This document covers the process for reporting bugs, proposing features, and submitting pull requests.

---

## Code of Conduct

Be respectful and constructive. Harassment or exclusionary behaviour will not be tolerated.

---

## How to Contribute

### Reporting bugs

1. Search [existing issues](https://github.com/Jagadeeshck/DataObs/issues) to avoid duplicates.
2. Open a new issue with:
   - A clear title and description
   - Steps to reproduce
   - Expected vs actual behaviour
   - Environment (OS, Python version, Docker version)
   - Relevant logs or config snippets

### Proposing features

Open a [GitHub Discussion](https://github.com/Jagadeeshck/DataObs/discussions) or an issue labelled `enhancement` with:
- The use case and motivation
- A rough implementation sketch
- Whether you are willing to implement it

### Submitting a pull request

#### 1. Fork and clone

```bash
git clone https://github.com/<your-username>/DataObs.git
cd DataObs
git remote add upstream https://github.com/Jagadeeshck/DataObs.git
```

#### 2. Create a branch

Use a descriptive branch name:

```bash
git checkout -b feat/spark-otel-instrumentation
git checkout -b fix/freshness-sla-edge-case
git checkout -b docs/update-helm-readme
```

#### 3. Set up the dev environment

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install pytest
```

#### 4. Make your changes

- Follow existing code style (PEP 8, type hints where present)
- Add or update tests for any changed behaviour
- Update relevant documentation (`docs/`, `README.md`) if needed
- Keep commits atomic and use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
feat(quality): add column distribution drift check
fix(api): handle empty lineage graph response
docs(helm): document all values.yaml options
chore(ci): pin trivy-action to specific version
```

#### 5. Run the test suite

```bash
python -m pytest tests/ -v --tb=short
```

All tests must pass before opening a PR.

#### 6. Validate configs (if you changed Alloy or OTel config)

```bash
# Install Alloy locally
curl -fsSL https://github.com/grafana/alloy/releases/download/v1.8.1/alloy-linux-amd64.zip \
  -o alloy.zip && unzip -q alloy.zip && chmod +x alloy-linux-amd64

# Check formatting
./alloy-linux-amd64 fmt --test integrations/grafana-alloy/alloy/config.alloy

# Auto-format if needed
./alloy-linux-amd64 fmt --write integrations/grafana-alloy/alloy/config.alloy
```

#### 7. Push and open a PR

```bash
git push origin feat/your-feature-name
```

Open a PR against `main`. The CI pipeline must pass (validate + test + build) before merge review.

---

## Project Structure

See the [Repository Layout](README.md#repository-layout) section in the README.

Key areas:

| Area | Location | Notes |
|------|----------|-------|
| Quality checks | `src/quality/checks/` | Inherit from `base.py` |
| REST API | `src/api/main.py` | FastAPI / lightweight HTTP |
| Alerting clients | `src/alerting/` | Each client is standalone |
| OTel config | `config/otel-collector-config.yaml` | Standard OTel Collector syntax |
| Alloy config | `integrations/grafana-alloy/alloy/config.alloy` | Grafana Alloy River syntax |
| K8s manifests | `k8s/` | Applied with `kubectl apply` |
| Helm chart | `helm/dataobs/` | `values.yaml` for all overrides |
| CI | `.github/workflows/ci.yml` | 4-job pipeline |

---

## Adding a New Quality Check

1. Create `src/quality/checks/your_check.py` inheriting from `BaseCheck`
2. Implement `run(self, context) -> CheckResult`
3. Add test coverage in `tests/test_quality_checks.py`
4. Register in `config/dataobs.example.yaml` under `quality.checks`

---

## Commit Signing

Commits to `main` are not required to be signed, but GPG-signed commits are welcomed.

---

## Questions

For general questions, open a [Discussion](https://github.com/Jagadeeshck/DataObs/discussions).
For bug reports, open an [Issue](https://github.com/Jagadeeshck/DataObs/issues).

## Team delivery workflow

Use `codex/<capability-name>` branches and identify the owning team in PR metadata. Follow [team ownership](docs/development/team-ownership.md), submit shared changes through the [contract sequence](docs/development/shared-contract-rules.md), and use an [ADR](docs/architecture/adr/README.md) only for cross-team decisions. Released migrations remain immutable under the [migration rules](docs/development/migration-ownership.md).
