# Implement a DataObs owned change

1. Identify team owner, user/pillar scope, baseline SHA, impacted API/service/UI/infra paths and exit criteria.
2. Create feature branch from latest main. Read matching steering and skill.
3. Reproduce current failure or define contract acceptance. Do not duplicate previously merged fixes.
4. Implement minimal owned change with unit, tenant/security, real-stack and UI tests as applicable.
5. Verify Black/Ruff/mypy or pnpm typecheck/lint/format/test/build; save evidence and no-skips statement.
6. Create small PR with root cause, affected contracts, proof and dependent-team review.
7. Hand over to release coordinator for ordered integration; do not merge/promote automatically.
