# Workflow deployment

Use `python -m integrations.elastic.workflows.deployer validate`, `plan`, `deploy`, or `status`. Deployment also requires `DATAOBS_ELASTIC_WORKFLOW_DEPLOYMENT_ENABLED=true` in production composition. The deploy credential is separate from runtime and limited to workflow create/read/update. Plan/status are read-only; deploy creates or explicitly reconciles a reviewed definition and never deletes remote workflows. Remote checksum differences are drift and are not silently overwritten by background synchronization.
