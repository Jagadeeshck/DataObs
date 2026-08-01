from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from packages.collectors.sdk.errors import InvalidConfigurationError

SERVICES = frozenset({"rds", "glue", "athena", "emr-serverless"})
REGION = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-\d$")
ACCOUNT = re.compile(r"^\d{12}$")
ROLE = re.compile(r"^arn:aws(?:-us-gov)?:iam::\d{12}:role/[A-Za-z0-9+=,.@_/-]{1,512}$")
ALLOWED = {
    "expected_account_id",
    "assume_role",
    "regions",
    "services",
    "resource_filters",
    "cloudwatch",
    "ownership_tag_keys",
    "limits",
    "history_overlap_seconds",
    "sts_endpoint_url",
}


@dataclass(frozen=True)
class AwsConfiguration:
    expected_account_id: str | None
    regions: tuple[str, ...]
    services: tuple[str, ...]
    raw: Mapping[str, Any]


def parse_configuration(raw: Mapping[str, Any]) -> AwsConfiguration:
    unknown = set(raw) - ALLOWED
    if unknown:
        raise InvalidConfigurationError("unknown AWS configuration keys")
    regions = tuple(raw.get("regions") or ())
    services = tuple(raw.get("services") or ())
    if not regions or len(regions) > 20 or any(not REGION.fullmatch(str(x)) for x in regions):
        raise InvalidConfigurationError("one to twenty explicit valid AWS regions are required")
    if not services or len(services) > len(SERVICES) or not set(services) <= SERVICES:
        raise InvalidConfigurationError("unsupported or empty AWS service selection")
    account = raw.get("expected_account_id")
    if account is not None and not ACCOUNT.fullmatch(str(account)):
        raise InvalidConfigurationError("invalid AWS account ID")
    role = raw.get("assume_role") or {}
    if set(role) - {"role_arn", "external_id_ref", "session_duration_seconds"}:
        raise InvalidConfigurationError("unknown assume_role key")
    if role and not ROLE.fullmatch(str(role.get("role_arn", ""))):
        raise InvalidConfigurationError("invalid role ARN")
    duration = int(role.get("session_duration_seconds", 3600))
    if not 900 <= duration <= 43200:
        raise InvalidConfigurationError("role session duration is out of bounds")
    cw = raw.get("cloudwatch") or {}
    if set(cw) - {"enabled", "lookback_seconds", "period_seconds"}:
        raise InvalidConfigurationError("unknown cloudwatch key")
    if not 60 <= int(cw.get("lookback_seconds", 900)) <= 86400:
        raise InvalidConfigurationError("CloudWatch lookback is out of bounds")
    if int(cw.get("period_seconds", 300)) not in range(60, 3601, 60):
        raise InvalidConfigurationError("CloudWatch period is out of bounds")
    filters = raw.get("resource_filters") or {}
    if set(filters) - {"include_tags", "exclude_tags"}:
        raise InvalidConfigurationError("unknown resource filter")
    if sum(len(v) for group in filters.values() for v in group.values()) > 100:
        raise InvalidConfigurationError("too many tag filters")
    if len(raw.get("ownership_tag_keys") or ()) > 20:
        raise InvalidConfigurationError("too many ownership tag keys")
    endpoint = raw.get("sts_endpoint_url")
    if endpoint and not str(endpoint).startswith(("http://localhost", "http://127.0.0.1")):
        raise InvalidConfigurationError("custom STS endpoints are test-only")
    return AwsConfiguration(str(account) if account else None, regions, services, raw)
