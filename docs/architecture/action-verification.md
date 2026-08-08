# Action verification

Provider acceptance is not execution proof and execution success is not recovery. An accepted action enters `verification_pending`. Evidence must be durable, bounded, match the target, and have an observation time after execution began.

`scan_task_v1`, `freshness_measurement_v1`, and `connection_test_v1` are declared strategies, but their executors remain unconfigured until a safe public service contract is certified. Verification records `verified_execution` separately from nullable `recovery_observed`; missing evidence is failure/pending, never success. No verification resolves an incident automatically.
