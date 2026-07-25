# Kafka Observer scale results

The collector never materializes a topic-partition-group Cartesian product: it walks broker-reported member assignments and stops at `maximum_combinations_per_cycle` (default 100,000; hard limit 1,000,000). Connect and Registry collectors similarly cap sources and emit continuation state. No million-combination benchmark was executed in this environment; throughput and peak-memory results therefore remain a draft-PR blocker rather than fabricated evidence.
