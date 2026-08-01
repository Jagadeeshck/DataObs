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


class CloudWatchAdapter:
    def __init__(
        self, client, *, lookback_seconds=900, period_seconds=300, maximum_queries=100, maximum_datapoints=1000
    ):
        self.client, self.lookback, self.period = client, lookback_seconds, period_seconds
        self.maximum_queries, self.maximum_datapoints = maximum_queries, maximum_datapoints

    def collect(self, resource_id, namespace, dimensions, definitions, now=None):
        now = now or datetime.now(timezone.utc)
        definitions = dict(list(definitions.items())[: self.maximum_queries])
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
        while True:
            response = self.client.get_metric_data(
                MetricDataQueries=queries,
                StartTime=now - timedelta(seconds=self.lookback),
                EndTime=now,
                **({"NextToken": token} if token else {}),
            )
            for result in response.get("MetricDataResults", []):
                results.setdefault(result["Id"], result).get("Values", []).extend([])
            token = response.get("NextToken")
            if not token:
                break
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
