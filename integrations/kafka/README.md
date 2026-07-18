# Kafka integration

The adapter performs metadata-only Admin operations. It never produces, consumes, changes configuration, deletes topics, or resets offsets. The observer needs Cluster `Describe`/`DescribeConfigs`, Topic `Describe`/`DescribeConfigs`, and Group `Describe`. Optional timestamp inspection requires Topic `Read` and is disabled by default.
