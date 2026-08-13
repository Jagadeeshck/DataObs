# Post-Incident Review

Team 3 owns a deterministic review identified by tenant, environment, incident and generation. Requirement (`not_required`, `required`, `waived`) is separate from lifecycle (`draft`, `in_review`, `completed`, `superseded`). Critical and high incidents are required under the persisted v1 policy decision and hash.

Creation snapshots the incident revision, evidence cutoff and durable timeline checkpoint. Refresh is explicit and preserves human sections. Completed generations are immutable; reopen creates a later generation linked with `supersedes` rather than rewriting history.

Facts and identifier-only evidence references seed a draft. Root cause dispositions are unknown, hypothesis, probable and confirmed. Confirmation requires a human principal; incident RCA candidates are never promoted automatically.
