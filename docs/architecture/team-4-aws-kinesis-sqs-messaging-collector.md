# Team 4 AWS Kinesis and SQS messaging collector

AWS provider v3 adds bounded provider-native Kinesis and SQS evidence to the existing `aws` Integration SDK provider. It does not introduce a messaging provider or canonical model. Team 1 remains authoritative for identity, Stream 360 normalization, and projections.

Kinesis uses only ListStreams, DescribeStreamSummary, ListShards, and ListTagsForStream. Evidence covers safe stream configuration, structural encryption, enhanced-monitoring categories, and shard parent/state topology. Hash and sequence ranges, KMS identities, partition keys, records, and policies are discarded. AWS/Kinesis metric names are closed; `GetRecords.IteratorAgeMilliseconds` retains the `iterator_age` meaning and is never offset lag.

SQS uses only ListQueues, an explicit GetQueueAttributes allowlist, and ListQueueTags. Policy, RedriveAllowPolicy, and KmsMasterKeyId are neither requested nor retained. RedrivePolicy is parsed immediately into a visible-scope redrive relationship. Queue depth fields are explicitly `provider_approximate`. Missing CloudWatch points remain missing, while measured zero remains zero.

The existing CloudWatch adapter supplies bounded GetMetricData collection. Per-resource failures emit safe partial failures without deleting successful siblings. Collection Manager continues to own durable append-before-checkpoint behavior and scoped checkpoints; no new scheduler, index, or migration is introduced. Status is **functional_unvalidated**, not production-ready or certified.
