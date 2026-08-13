# DataObs rollback runbook

Use the canonical rollback classification before change. `application_only` permits only the image/chart portion described by certification; a migration or configuration barrier prohibits ordinary rollback. Do not reverse destructive migrations. Use the existing backup/restore and DR documentation for recovery and retain checksums and exact SHAs.
