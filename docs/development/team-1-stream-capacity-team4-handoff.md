# Team 1 / Team 4 capacity evidence handoff

Collectors should provide non-negative timestamped measurements with method and evidence reference; separately sourced
positive limits with unit, scope, authority and confidence; throttle/rejection facts; topology counts; and bounded
partition/shard series. Kinesis on-demand must not provide a fabricated fixed limit. SQS backlog metrics remain
provider-approximate and are never mapped to Kafka lag. Missing Event Hubs checkpoints remain missing, not zero.
