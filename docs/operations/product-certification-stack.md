# Operating the product certification stack

Use `./scripts/certification/compose.sh config`, `up core` (or `up full`), `seed`, `test backend`, `test browser`, `test security`, `evidence`, then `down`. Set `CERTIFICATION_PROFILE=postgres|kafka|jobs` for a focused run. Allow 8 CPU, 16 GiB RAM, 30 GiB free disk; macOS and Linux are supported.

Troubleshooting: increase Docker memory for Elasticsearch exits; use `down` to remove stale volumes; change only loopback host mappings for port conflicts; inspect `compose ps` for unhealthy Elastic/Kibana; wait within the bounded startup window; inspect broker quorum and Registry/Connect ordering for Kafka; keep Playwright image/package pins equal; treat a redaction failure as a hard security failure and delete the artifact rather than bypassing it.

Certification disables Elastic security on internal isolated networks and uses local development identity. Never copy these defaults to production. Teardown is mandatory and CI runs it under `always()`.
