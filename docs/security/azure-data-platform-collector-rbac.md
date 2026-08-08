# Least-privilege Azure RBAC

Prefer managed identity, then workload identity, and use a referenced service-principal secret only when necessary. Scope management-plane Reader permissions to each synthetic resource or resource group rather than the subscription wherever feasible.

Required read actions are subscription validation; `Microsoft.DataFactory/factories/read`, pipeline/trigger/read and query pipeline/activity runs; `Microsoft.Synapse/workspaces/read`, SQL pool/read, big-data pool/read, pipeline/read and run-history read; and `Microsoft.Storage/storageAccounts/read`. Do not grant Data Factory Contributor, Synapse Administrator, SQL database permissions, Storage Account Contributor, Owner, or Contributor. No start, cancel, pool mutation, key-list, or SAS action is needed.

Filesystem/path listing is data-plane access, separate from management-plane metadata. When enabled, narrowly scope Storage Blob Data Reader (for example, synthetic account `stdataobsdev` or a specific container). That role may also authorize content reads, so assignments must be minimal and provider code independently denies/download-free operation. Do not use Storage Blob Data Owner. Prefix listing is optional and disabled by default.
