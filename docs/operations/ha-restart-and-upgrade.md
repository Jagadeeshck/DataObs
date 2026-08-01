# Beta restart, upgrade, and rollback rehearsal

The authoritative bounded harnesses are `kind_smoke_test.sh` and
`helm_upgrade_test.sh`. They require digest-pinned values and an external
Elasticsearch service; the chart does not install Elasticsearch. They exercise
install/readiness, a rolling API replacement, an unchanged upgrade, and Helm
rollback. Kubernetes resource rollback never reverses forward-only migrations.

Durable-state, lease-expiry, append-only duplication, and continuous-availability
claims require hosted evidence from the exact candidate commit. Until that
artifact exists these controls are **implemented, locally inspectable, pending
hosted validation, and not production certified**.
