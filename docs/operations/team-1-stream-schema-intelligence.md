# Operating Team 1 stream schema intelligence

Collect at most 1,000 subjects per cycle and 100 versions per subject; evaluate at most 25 historical versions. Registry timeouts, authentication, authorization, rate limits, parse failures, and partial collection are availability states, not incompatibility.

Workers must use the existing fenced lease/checkpoint runtime. Append identities are deterministic; mutable projections require sequence number and primary term. Reconciliation replays retained version, compatibility, and impact evidence before advancing the scoped checkpoint.

Health exposes configuration, registry state, collection/evaluation timestamps, bounded counters, exposure/degradation counts, pending reconciliation, lease/heartbeat, and safe error codes. Never expose exception text.
