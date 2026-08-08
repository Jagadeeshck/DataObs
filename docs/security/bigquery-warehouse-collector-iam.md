# BigQuery collector least-privilege IAM

Use synthetic identities in examples. Grant `roles/bigquery.metadataViewer` on selected datasets, or monitored projects only when project inventory is required. It supports metadata without table-row reads; do not default to `roles/bigquery.dataViewer` because that includes data reads.

Fixed regional metadata queries require `bigquery.jobs.create`, typically `roles/bigquery.jobUser` on the synthetic collector/billing project, plus metadata/history visibility on monitored projects and explicit locations. Project-wide jobs and optional reservations require `roles/bigquery.resourceViewer` or a narrower custom read-only role. For impersonation, grant the source principal `roles/iam.serviceAccountTokenCreator` only on `dataobs-bigquery@synthetic-project.iam.gserviceaccount.com`, use short tokens, and avoid keys.

Never recommend Owner, Editor, BigQuery Admin, Data Owner, Data Editor, broad table data access, organisation viewer, or billing administrator. WIF is preferred outside Google Cloud. Credential material, principal identity, tokens, auth diagnostics, SQL, response bodies and sensitive metadata must not be persisted or added to telemetry.
