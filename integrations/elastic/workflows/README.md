# Elastic Workflows integration

DataObs workflow packs are YAML files deployed through public Kibana Workflows APIs. Alert-trigger workflows must also be attached to Kibana alert rules with a Run Workflow action; the validator fails workflow YAML that declares an alert trigger without `runWorkflowActionRequired: true`. Cases steps use `cases.*`, not deprecated `kibana.*` aliases. Credentials are supplied by secret references/environment variables and are never stored in workflow YAML.

Technical-preview event triggers and Streams enrichment are optional only; the periodic execution synchronizer is the stable fallback for workflow-failure handling.
