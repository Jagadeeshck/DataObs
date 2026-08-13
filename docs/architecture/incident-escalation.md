# Incident escalation

Escalation consumes the authoritative response-objective result and staleness state; it does not calculate SLOs. Policies use neutral `level_1` through `level_3` and versioned advancement/cooldown intervals. Identity hashes tenant, environment, incident, trigger, initial level, and policy version.

The current projection and append-only event history are separate. Atomic create/update semantics suppress repeated polling events and worker races. Trigger removal clears current state without deleting history. Escalation acknowledgement is separate from incident acknowledgement and escalation never changes severity.
