from __future__ import annotations

from datetime import datetime, timedelta, timezone

from packages.collectors.sdk import EvidenceState, MetricObservation

RDS_METRICS = {
    "CPUUtilization": ("percent", "Average"),
    "FreeStorageSpace": ("bytes", "Average"),
    "DatabaseConnections": ("count", "Average"),
    "ReadLatency": ("seconds", "Average"),
    "WriteLatency": ("seconds", "Average"),
    "ReadIOPS": ("count/second", "Average"),
    "WriteIOPS": ("count/second", "Average"),
}

KINESIS_METRICS = {
    "IncomingBytes": ("bytes", "Sum"),
    "IncomingRecords": ("count", "Sum"),
    "GetRecords.Bytes": ("bytes", "Sum"),
    "GetRecords.Records": ("count", "Sum"),
    "GetRecords.IteratorAgeMilliseconds": ("milliseconds", "Maximum"),
    "ReadProvisionedThroughputExceeded": ("count", "Sum"),
    "WriteProvisionedThroughputExceeded": ("count", "Sum"),
    "PutRecords.FailedRecords": ("count", "Sum"),
    "PutRecords.ThrottledRecords": ("count", "Sum"),
}

SQS_METRICS = {
    "ApproximateNumberOfMessagesVisible": ("count", "Average"),
    "ApproximateNumberOfMessagesNotVisible": ("count", "Average"),
    "ApproximateNumberOfMessagesDelayed": ("count", "Average"),
    "ApproximateAgeOfOldestMessage": ("seconds", "Maximum"),
    "NumberOfMessagesSent": ("count", "Sum"),
    "NumberOfMessagesReceived": ("count", "Sum"),
    "NumberOfMessagesDeleted": ("count", "Sum"),
    "SentMessageSize": ("bytes", "Average"),
}

METRIC_REGISTRY = {
    "rds": ("AWS/RDS", ("DBInstanceIdentifier",), RDS_METRICS, 300, 100),
    "glue": ("Glue", ("JobName", "Type"), {}, 300, 100),
    "athena": ("AWS/Athena", ("WorkGroup",), {}, 300, 100),
    "emr-serverless": ("AWS/EMRServerless", ("ApplicationId", "JobId"), {}, 300, 100),
    "s3": (
        "AWS/S3",
        ("BucketName", "StorageType", "FilterId"),
        {
            "BucketSizeBytes": ("bytes", "Average"),
            "NumberOfObjects": ("count", "Average"),
            "AllRequests": ("count", "Sum"),
            "GetRequests": ("count", "Sum"),
            "PutRequests": ("count", "Sum"),
            "4xxErrors": ("count", "Sum"),
            "5xxErrors": ("count", "Sum"),
            "FirstByteLatency": ("milliseconds", "Average"),
            "TotalRequestLatency": ("milliseconds", "Average"),
        },
        86400,
        50,
    ),
    "lambda": (
        "AWS/Lambda",
        ("FunctionName", "Resource", "ExecutedVersion"),
        {
            name: (
                "milliseconds" if name == "Duration" else "count",
                "Average" if name in {"Duration", "ConcurrentExecutions"} else "Sum",
            )
            for name in (
                "Invocations",
                "Errors",
                "Throttles",
                "Duration",
                "ConcurrentExecutions",
                "ProvisionedConcurrencyInvocations",
                "ProvisionedConcurrencySpilloverInvocations",
                "DeadLetterErrors",
                "IteratorAge",
            )
        },
        300,
        100,
    ),
    "sagemaker": (
        "AWS/SageMaker",
        ("EndpointName", "VariantName", "Host", "TrainingJobName"),
        {
            name: (
                "milliseconds" if "Latency" in name else "percent" if "Utilization" in name else "count",
                "Average" if "Latency" in name or "Utilization" in name else "Sum",
            )
            for name in (
                "Invocations",
                "Invocation4XXErrors",
                "Invocation5XXErrors",
                "ModelLatency",
                "OverheadLatency",
                "CPUUtilization",
                "MemoryUtilization",
                "GPUUtilization",
                "DiskUtilization",
            )
        },
        300,
        100,
    ),
    "mwaa": (
        "AmazonMWAA",
        ("Environment", "Function", "Dimension"),
        {
            name: ("percent" if "Utilization" in name else "count", "Average")
            for name in (
                "SchedulerHeartbeat",
                "TotalParseTime",
                "DagBagSize",
                "ImportErrors",
                "QueuedTasks",
                "RunningTasks",
                "OpenSlots",
                "TasksPending",
                "TasksRunning",
                "SchedulerTasks",
                "CPUUtilization",
                "MemoryUtilization",
            )
        },
        300,
        100,
    ),
    "redshift": (
        "AWS/Redshift",
        ("ClusterIdentifier", "NodeID", "service class"),
        {
            name: (
                "percent" if name in {"CPUUtilization", "HealthStatus", "PercentageDiskSpaceUsed"} else "count",
                "Average",
            )
            for name in (
                "CPUUtilization",
                "DatabaseConnections",
                "HealthStatus",
                "PercentageDiskSpaceUsed",
                "ReadIOPS",
                "WriteIOPS",
                "ReadLatency",
                "WriteLatency",
                "NetworkReceiveThroughput",
                "NetworkTransmitThroughput",
                "QueryDuration",
                "QueryRuntimeBreakdown",
            )
        },
        300,
        100,
    ),
    "redshift-serverless": (
        "AWS/Redshift-Serverless",
        ("Workgroup", "Database"),
        {
            name: ("count", "Average")
            for name in (
                "ComputeCapacity",
                "ComputeSeconds",
                "DatabaseConnections",
                "QueriesCompletedPerSecond",
                "QueryDuration",
                "QueriesQueued",
                "RunningQueries",
            )
        },
        300,
        100,
    ),
    "kinesis": ("AWS/Kinesis", ("StreamName", "ShardId"), KINESIS_METRICS, 300, 100),
    "sqs": ("AWS/SQS", ("QueueName",), SQS_METRICS, 300, 100),
}


def metric_definition(service, metric_name):
    """Resolve only registry-backed metrics; arbitrary caller definitions are rejected."""
    namespace, dimensions, definitions, expected_period, query_limit = METRIC_REGISTRY[service]
    if metric_name not in definitions:
        raise ValueError("metric is not allowlisted")
    return namespace, dimensions, definitions[metric_name], expected_period, query_limit


class CloudWatchAdapter:
    def __init__(
        self, client, *, lookback_seconds=900, period_seconds=300, maximum_queries=100, maximum_datapoints=1000
    ):
        self.client, self.lookback, self.period = client, lookback_seconds, period_seconds
        self.maximum_queries, self.maximum_datapoints = maximum_queries, maximum_datapoints

    def collect(self, resource_id, namespace, dimensions, definitions, now=None):
        now = now or datetime.now(timezone.utc)
        allowed_namespaces = {entry[0] for entry in METRIC_REGISTRY.values()}
        if namespace not in allowed_namespaces:
            raise ValueError("CloudWatch namespace is not allowlisted")
        registry_entries = [entry for entry in METRIC_REGISTRY.values() if entry[0] == namespace]
        allowed_metrics = set().union(*(entry[2] for entry in registry_entries))
        allowed_dimensions = set().union(*(entry[1] for entry in registry_entries))
        if not set(definitions) <= allowed_metrics:
            raise ValueError("CloudWatch metric is not allowlisted")
        if not set(dimensions) <= allowed_dimensions:
            raise ValueError("CloudWatch dimension is not allowlisted")
        definitions = dict(sorted(definitions.items())[: self.maximum_queries])
        queries = [
            {
                "Id": f"m{i}",
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": name,
                        "Dimensions": [{"Name": k, "Value": v} for k, v in sorted(dimensions.items())],
                    },
                    "Period": self.period,
                    "Stat": stat,
                },
                "ReturnData": True,
            }
            for i, (name, (_, stat)) in enumerate(definitions.items())
        ]
        response, token, results = {}, None, {}
        # GetMetricData pagination is bounded independently of the provider's retry policy.
        for _ in range(100):
            response = self.client.get_metric_data(
                MetricDataQueries=queries,
                StartTime=now - timedelta(seconds=self.lookback),
                EndTime=now,
                **({"NextToken": token} if token else {}),
            )
            for result in response.get("MetricDataResults", []):
                stored = results.setdefault(result["Id"], {"Values": [], "Timestamps": []})
                remaining = self.maximum_datapoints - len(stored["Values"])
                if remaining > 0:
                    stored["Values"].extend(result.get("Values", [])[:remaining])
                    stored["Timestamps"].extend(result.get("Timestamps", [])[:remaining])
            token = response.get("NextToken")
            if not token:
                break
        else:
            # Bounded partial metric evidence is preferable to an unbounded provider loop.
            token = None
        output = []
        for i, (name, (unit, stat)) in enumerate(definitions.items()):
            result = results.get(f"m{i}", {})
            values = result.get("Values", [])
            timestamps = result.get("Timestamps", [])
            measured = bool(values)
            output.append(
                MetricObservation(
                    resource_id,
                    name,
                    float(values[0]) if measured else None,
                    EvidenceState.MEASURED if measured else EvidenceState.MISSING,
                    unit,
                    stat.lower(),
                    self.period,
                    timestamps[0] if measured and timestamps else now,
                    "aws",
                )
            )
        return sorted(output, key=lambda metric: metric.metric_name)
