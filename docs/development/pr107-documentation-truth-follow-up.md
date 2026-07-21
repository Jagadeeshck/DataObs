# PR #107 documentation-truth follow-up

PR #107 was merged by commit `0b9c53d`. This follow-up records the four review findings without claiming that a local run is hosted evidence.

| Finding | Original problem | Fixing commit | Test | CI job | Result |
|---|---|---|---|---|---|
| P1 capability base | The workflow dereferenced a pull-request-only event field. | First commit on this branch | `test_resolve_pull_request_base`, `test_resolve_push_base`, `test_resolve_workflow_dispatch_explicit_input`, `test_resolve_all_zero_push_uses_merge_base` | `documentation-truth-gate` | Local contract passed; hosted result pending. |
| P2 migration immutability | A migration and mutable ledger checksum could be changed together. | First commit on this branch | `test_checksum_mutation_is_rejected_by_id`, `test_disappearance_and_reordering_are_rejected` | migration, documentation, and certification contract gates | Local contract passed; hosted result pending. |
| P2 validated evidence | Empty or all-not-applicable evidence could support `validated`. | First commit on this branch | future AI and FinOps negative cases in `test_ci_truth_tools.py` | `documentation-truth-gate` | Local contract passed; hosted result pending. |
| P2 transition completeness | Deprecated and optional-integration transitions disappeared. | First commit on this branch | `test_special_state_transitions_are_never_dropped` | `documentation-truth-gate` | Local contract passed; hosted result pending. |

Old review threads should be resolved only after the fixing commit and a hosted CI result are linked. Migrations `0001` through `0012` were not edited by this follow-up.
