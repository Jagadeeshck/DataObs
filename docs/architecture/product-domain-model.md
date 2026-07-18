# Product domain model

DataObs product state uses tenant-aware Pydantic contracts in `packages/domain_model`. Product entities carry deterministic IDs, `tenant_id`, `environment`, schema version, timestamps, ownership, pillar, labels, annotations, and correlation fields. Secrets are represented by credential references and endpoint metadata rejects secret-like keys.
