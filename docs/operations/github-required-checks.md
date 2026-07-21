# GitHub required certification checks

Require these status checks on `main`: **Documentation truth gate**, **Certification contracts**, **Certification migrations and incidents**, **Certification PostgreSQL**, **Certification Kafka**, **Certification OpenLineage and product queries**, **Certification browser**, **Certification security**, and **Certification summary**.

This repository checkout has no authenticated GitHub CLI, so branch protection has **not** been configured or verified. An administrator must open **Settings → Branches → Branch protection rules → main**, enable “Require status checks to pass before merging”, search for the exact names above after their first run, select all checks, and save without enabling automatic merge. Equivalent API operation: update `repos/Jagadeeshck/DataObs/branches/main/protection` with `required_status_checks.strict=true` and those contexts, then GET the same endpoint and retain the response as administrative evidence.

The PR must remain draft/open while certification runs. Actions and hosted-run permissions must be verified in **Settings → Actions → General**. No successful local run substitutes for hosted evidence.
