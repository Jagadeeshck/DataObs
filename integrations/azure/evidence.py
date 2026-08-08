LIMITATIONS = (
    "Only explicitly configured Azure Public Cloud resources are observed",
    "Pipeline records are source evidence, not canonical jobs or lineage",
    "SQL text, parameters, activity input/output, identities, secrets, paths and file contents are excluded",
    "ADLS modification time is storage-object freshness, not business-data freshness",
    "No production-readiness or certification claim exists without exact-commit hosted evidence",
)
CHECKPOINT_FAMILIES = (
    "adf.pipeline",
    "adf.trigger",
    "adf.pipeline_run",
    "adf.activity_run",
    "synapse.workspace_pool",
    "synapse.pipeline",
    "synapse.pipeline_run",
    "synapse.activity_run",
    "adls.filesystem",
    "adls.prefix_observation",
)
