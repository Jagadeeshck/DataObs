# Data SLO migration and recovery

Apply the normal Elasticsearch migration runner and require migration doctor to report the contiguous terminal `0032_team2_data_slo_production_runtime`. Retry is safe. On worker loss, wait for lease expiry; the replacement obtains a higher fencing token. The old worker cannot publish current state or checkpoint. Immutable evaluation create conflicts mean an identical replay already completed and are not overwritten.

Rollback is operational: stop SLO workers and API mutations, retain definition events and evaluation history, and leave additive strict resources in place. Restore service only after mapping readiness and migration doctor succeed.
