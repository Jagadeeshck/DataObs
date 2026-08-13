# AWS messaging collector least-privilege access

Allow Kinesis `ListStreams`, `DescribeStreamSummary`, `ListShards`, and `ListTagsForStream`; SQS `ListQueues`, `GetQueueAttributes`, and `ListQueueTags`; shared `cloudwatch:GetMetricData` and `sts:GetCallerIdentity`. The existing optional AssumeRole architecture may additionally require `sts:AssumeRole` on the configured role.

Do **not** grant Kinesis GetRecords, GetShardIterator, SubscribeToShard, PutRecord/PutRecords, monitoring changes, or stream mutations. Do **not** grant SQS ReceiveMessage, SendMessage, DeleteMessage, ChangeMessageVisibility, PurgeQueue, queue mutation, or message-move actions. Negative unit/static tests use clients that fail immediately if these methods are accessed, proving payload-read permissions are unnecessary.

GetQueueAttributes requests a closed list that excludes Policy, RedriveAllowPolicy, and KmsMasterKeyId. RedrivePolicy is reduced to target ARN and receive count before persistence. Kinesis KMS key IDs, hash/sequence ranges, records, payloads, partition keys, receipt handles, credentials/tokens, arbitrary secret-like tags, policies, and raw exceptions are never retained.
