from __future__ import annotations

from datetime import datetime

from packages.domain_model.incident import Finding, deterministic_id


def time_bucket(dt: datetime, minutes: int = 60) -> str:
    epoch = int(dt.timestamp())
    return str(epoch - (epoch % (minutes * 60)))


def deduplication_key(finding: Finding, bucket_minutes: int = 60) -> str:
    return deterministic_id(
        "dedup",
        [
            finding.tenant_id,
            finding.environment,
            finding.asset_id,
            str(finding.finding_type),
            finding.monitor_id or finding.policy_id or "none",
            time_bucket(finding.first_observed_at, bucket_minutes),
        ],
    )
