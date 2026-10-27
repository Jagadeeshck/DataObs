REGIONAL_BACKLOG_METRICS = frozenset(
    {
        "pubsub.googleapis.com/subscription/num_unacked_messages_by_region",
        "pubsub.googleapis.com/subscription/oldest_unacked_message_age_by_region",
        "pubsub.googleapis.com/subscription/unacked_bytes_by_region",
    }
)
GLOBAL_FALLBACK_METRICS = frozenset(
    {
        "pubsub.googleapis.com/subscription/num_undelivered_messages",
        "pubsub.googleapis.com/subscription/oldest_unacked_message_age",
        "pubsub.googleapis.com/subscription/backlog_bytes",
    }
)
DELIVERY_METRICS = frozenset(
    {
        "pubsub.googleapis.com/subscription/sent_message_count",
        "pubsub.googleapis.com/subscription/ack_message_count",
        "pubsub.googleapis.com/subscription/expired_ack_deadlines_count",
        "pubsub.googleapis.com/subscription/dead_letter_message_count",
        "pubsub.googleapis.com/topic/send_request_count",
    }
)
ALLOWED_METRICS = REGIONAL_BACKLOG_METRICS | GLOBAL_FALLBACK_METRICS | DELIVERY_METRICS


def validate_metric(metric_name: str) -> str:
    if metric_name not in ALLOWED_METRICS:
        raise ValueError("metric is not in the fixed Pub/Sub allowlist")
    return metric_name


def point_value(point):
    value = getattr(point, "value", None)
    for name in ("double_value", "int64_value"):
        candidate = getattr(value, name, None)
        if candidate is not None:
            return float(candidate)
    distribution = getattr(value, "distribution_value", None)
    return float(distribution.mean) if distribution is not None and getattr(distribution, "count", 0) else None


def collect_metric_series(
    client, project_id: str, metric_name: str, interval, alignment_seconds: int, maximum_series: int
):
    """Issue only an internally built allowlisted Monitoring query."""
    metric_name = validate_metric(metric_name)
    request = {
        "name": f"projects/{project_id}",
        "filter": f'metric.type = "{metric_name}"',
        "interval": interval,
        "view": "FULL",
        "aggregation": {
            "alignment_period": {"seconds": alignment_seconds},
            "per_series_aligner": "ALIGN_SUM" if metric_name in DELIVERY_METRICS else "ALIGN_MEAN",
        },
    }
    for index, series in enumerate(client.invoke("list_time_series", request=request), start=1):
        if index > maximum_series:
            raise RuntimeError("metric_series_limit_reached")
        yield series
