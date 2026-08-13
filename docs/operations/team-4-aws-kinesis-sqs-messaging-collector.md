# Operating the AWS Kinesis and SQS messaging collector

Enable `kinesis` and/or `sqs` in the existing AWS provider v3 configuration and prefer explicit `include_streams`/`include_queues` allowlists for live validation. Keep default pagination and CloudWatch limits unless an inventory audit justifies a bounded increase. `result_truncated=true` means evidence is incomplete.

Grant only the permissions in the security guide. AccessDenied on one resource becomes a stable partial failure; already collected siblings remain available and a failed logical scope must not advance its checkpoint. Troubleshoot account, region, service permission, throttling, and CloudWatch permission without recording raw AWS exception text.

Inactive queues commonly have missing CloudWatch datapoints; do not interpret them as zero. SQS attribute counts are approximate. Kinesis iterator age is milliseconds of iterator age, not consumer-group or committed-offset lag. Live tests are opt-in through `RUN_AWS_KINESIS_INTEGRATION_TESTS=1` or `RUN_AWS_SQS_INTEGRATION_TESTS=1` and require explicit disposable-resource allowlists. Tests never create, mutate, delete, receive, or consume.

Rollback by disabling the two services while retaining evidence/checkpoints. No Elasticsearch migration is associated with this collector.
