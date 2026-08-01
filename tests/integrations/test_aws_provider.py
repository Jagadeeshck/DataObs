import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from integrations.aws.cloudwatch import RDS_METRICS, CloudWatchAdapter
from integrations.aws.configuration import parse_configuration
from integrations.aws.provider import AwsDataPlatformProvider
from packages.collectors.sdk import Capability, CollectionRequest, EvidenceState, IntegrationContext
from packages.collectors.sdk.errors import InvalidConfigurationError, UnsupportedCapabilityError

CONFIG = {
    "expected_account_id": "000000000000",
    "regions": ["eu-west-1"],
    "services": ["rds"],
    "cloudwatch": {"enabled": True, "lookback_seconds": 900, "period_seconds": 300},
}


class Client:
    def describe_db_instances(self, **kwargs):
        return {
            "DBInstances": [
                {
                    "DBInstanceArn": "arn:aws:rds:eu-west-1:000000000000:db:synthetic",
                    "DBInstanceIdentifier": "synthetic-db",
                    "Engine": "postgres",
                    "Endpoint": {"Address": "forbidden.invalid"},
                }
            ]
        }

    def describe_db_clusters(self, **kwargs):
        return {"DBClusters": []}

    def list_tags_for_resource(self, **kwargs):
        return {"TagList": []}


class Factory:
    def __init__(self, cfg):
        pass

    def client(self, account, region, service):
        return Client()


def context():
    return IntegrationContext("tenant-a", "aws-a", "run-a", datetime.now(timezone.utc) + timedelta(seconds=5))


def test_explicit_regions_and_allowlist():
    with pytest.raises(InvalidConfigurationError):
        parse_configuration({"services": ["rds"]})
    with pytest.raises(InvalidConfigurationError):
        parse_configuration({"regions": ["eu-west-1"], "services": ["s3"]})


def test_provider_collects_safe_rds_and_rejects_capability():
    async def scenario():
        provider = AwsDataPlatformProvider(Factory)
        assert (await provider.validate_configuration(context(), CONFIG)).valid
        values = [
            x async for x in provider.collect(context(), CollectionRequest(frozenset({Capability.RESOURCE_DISCOVERY})))
        ]
        assert len(values) == 1 and "Endpoint" not in values[0].source_evidence
        with pytest.raises(UnsupportedCapabilityError):
            [x async for x in provider.collect(context(), CollectionRequest(frozenset({Capability.LOG_COLLECTION})))]

    asyncio.run(scenario())


def test_cloudwatch_measured_zero_and_missing():
    class CW:
        def get_metric_data(self, **kwargs):
            return {"MetricDataResults": [{"Id": "m0", "Values": [0], "Timestamps": [datetime.now(timezone.utc)]}]}

    values = CloudWatchAdapter(CW()).collect(
        "resource", "AWS/RDS", {"DBInstanceIdentifier": "synthetic"}, dict(list(RDS_METRICS.items())[:2])
    )
    assert values[0].value == 0 and values[0].state == EvidenceState.MEASURED
    assert values[1].value is None and values[1].state == EvidenceState.MISSING
