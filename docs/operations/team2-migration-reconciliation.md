# Team 2 migration reconciliation

Run `./bin/dataobs elastic doctor` before `apply`. Doctor is read-only and exits 2 when the chain is not ready.

## Clean environment

Apply the current chain normally. Migration 0029 follows 0028 and provisions the missing Team 2 projections, strict templates, and retention policies.

## Environment stopped before conflicting IDs

Export the migration status, run doctor, then apply normally if no conflict is reported.

## Historical 0026 Lineage migration

A stored 0026 checksum/name that does not identify the released stream migration produces `migration_registry_conflict`; application stops before later operations. Do not edit the state document. Export state and mappings, inventory actual Lineage resources, verify the historical/current checksums, retain the evidence bundle, and request explicit Team 0 approval for a reviewed manual reconciliation plan.

## Historical 0027 Data Contract migration

A stored 0027 identity that does not identify the released platform migration follows the same fail-closed procedure. Verify contract projections and immutable streams independently before proposing any state reconciliation.

## Both historical branch migrations

The chain is ambiguous and must remain stopped. Export both documents plus resource/template/ILM evidence. There is no automated or destructive rewrite path.

## Required operator evidence

Retain cluster UUID, repository SHA, UTC time, full state-index export, expected and observed names/checksums, templates, mappings, ILM policies, resource counts, redaction report, proposed action, reviewer, and Team 0 approval. Snapshot mutable projections first; immutable event streams are retained.
