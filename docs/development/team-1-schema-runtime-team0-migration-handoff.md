# Team 1 schema runtime — Team 0 migration handoff

PR #264 merged a Team 1 migration definition after deriving 0032 from an earlier main. Parallel PR #267 subsequently
registered Team 2's 0032; the merge reconciliation retained Team 1's definition but omitted it from `migrations()`.
The old orphan was `0032_team1_stream_schema_intelligence_runtime`; the new active forward migration is
`0033_team1_stream_schema_intelligence_runtime`, dependent on `0032_team2_data_slo_production_runtime`.

Repository evidence shows the old ID was neither executable nor capability-ledgered and contains no applied-state
document or artifact for it. External supported environments were unavailable for inspection. If Team 0 possesses
contrary applied-state evidence, this PR must stop and use the collision escalation procedure rather than merge.

The final registry checksum is `47a6f9ba7de57a4336972b18fa75da7430c4f621e71f76c02f80c77062823a69` and 0033 checksum is
`c53af6951bd1fa728981343272ea68c5cace73d68c5ed16d51ddf9fed785aec1`. Local registry, ledger, mapping, runtime,
privacy, fencing, OCC, replay and checkpoint tests pass. Clean install, Team-2-to-Team-1 upgrade, repeat live apply,
and doctor are workflow-gated on Elasticsearch 9.4.2 and have no local result because Elasticsearch/Docker is absent.

Team 0 review is explicitly required for the shared production Helm terminal change from stale 0030 to authoritative
0033 and for confirmation that no supported cluster applied the orphan identity. Before approval, inspect the hosted
migration-state index, run the reconciliation workflow, and retain its clean-install, upgrade, repeat-apply and doctor
artifact. Do not approve if any cluster reports the old Team 1 0032; export that state and escalate the numeric
collision instead.
