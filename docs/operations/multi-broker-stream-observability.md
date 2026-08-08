# Operating multi-broker Stream 360

Check `/api/v1/streams/providers` before enabling provider-specific sections. `not_configured`, `unsupported`, and missing evidence are distinct states. Configure read-only Team 4 integrations and verify observation freshness and coverage; never use receive, acknowledge, peek, GetRecords, purge, bind, or mutation APIs.

The current terminal migration remains `0028_pathway_investigation_history`; no durable multi-broker projection migration is claimed by this contract increment. Rollback removes adapter/API changes only and leaves released migrations and evidence untouched.
