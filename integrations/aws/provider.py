from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic

from packages.collectors.sdk import (
    Capability,
    CollectionMode,
    ConnectionTestResult,
    PartialFailure,
    ProviderCapabilities,
    ValidationIssue,
    ValidationResult,
)
from packages.collectors.sdk.errors import IntegrationError

from .clients import AwsClientFactory
from .configuration import parse_configuration
from .errors import map_aws_error
from .services import (
    athena,
    emr_serverless,
    glue,
    lambda_service,
    mwaa,
    rds,
    redshift,
    redshift_serverless,
    s3,
    sagemaker,
)

AWS_CLIENT_NAMES = {
    "rds": "rds",
    "glue": "glue",
    "athena": "athena",
    "emr-serverless": "emr-serverless",
    "s3": "s3",
    "lambda": "lambda",
    "sagemaker": "sagemaker",
    "mwaa": "mwaa",
    "redshift": "redshift",
    "redshift-serverless": "redshift-serverless",
}

COLLECTORS = {
    "rds": rds.collect,
    "glue": glue.collect,
    "athena": athena.collect,
    "emr-serverless": emr_serverless.collect,
    "s3": s3.collect,
    "lambda": lambda_service.collect,
    "sagemaker": sagemaker.collect,
    "mwaa": mwaa.collect,
    "redshift": redshift.collect,
    "redshift-serverless": redshift_serverless.collect,
}


class AwsDataPlatformProvider:
    provider_type = "aws"
    provider_version = "2"

    def __init__(self, client_factory=None):
        self._factory = client_factory

    def capabilities(self):
        supported = frozenset(
            {
                Capability.RESOURCE_DISCOVERY,
                Capability.METADATA_COLLECTION,
                Capability.METRIC_COLLECTION,
                Capability.HEALTH_CHECK,
                Capability.INCREMENTAL_COLLECTION,
            }
        )
        return ProviderCapabilities(
            supported,
            frozenset(set(Capability) - set(supported)),
            ("sts:GetCallerIdentity", "read-only service metadata", "cloudwatch:GetMetricData"),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            ("boto3",),
            (
                "Ten explicitly configured services only",
                "No object contents, SQL, secrets, logs, lineage, profiling, cost, or mutation",
            ),
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_configuration(configuration)
            return ValidationResult(True)
        except IntegrationError as exc:
            return ValidationResult(False, (ValidationIssue(str(exc.code), "provider", str(exc)),))

    def _clients(self, cfg):
        return self._factory(cfg) if self._factory else AwsClientFactory(cfg)

    async def test_connection(self, context, configuration):
        started = monotonic()
        try:
            cfg = parse_configuration(configuration)
            factory = self._clients(cfg)
            identity = factory.client(cfg.expected_account_id or "unknown", cfg.regions[0], "sts").get_caller_identity()
            if cfg.expected_account_id and identity.get("Account") != cfg.expected_account_id:
                return ConnectionTestResult(
                    False, error_code="account_mismatch", message="AWS account does not match configuration"
                )
            return ConnectionTestResult(True, int((monotonic() - started) * 1000))
        except IntegrationError as exc:
            return ConnectionTestResult(False, error_code=str(exc.code), message=str(exc))
        except Exception as exc:
            safe = map_aws_error(exc)
            return ConnectionTestResult(False, error_code=str(safe.code), message=str(safe))

    async def discover(self, context, request):
        async for item in self.collect(
            context, type("Request", (), {"capabilities": frozenset({Capability.RESOURCE_DISCOVERY})})()
        ):
            if not isinstance(item, PartialFailure):
                yield item

    async def collect(self, context, request):
        self.capabilities().require(request.capabilities)
        cfg = self._configuration
        factory = self._clients(cfg)
        account = cfg.expected_account_id or "unknown"
        # Region/service loops intentionally isolate failures and remain bounded by validated configuration.
        for region in cfg.regions:
            for service in cfg.services:
                try:
                    client = factory.client(account, region, AWS_CLIENT_NAMES[service])
                    for item in COLLECTORS[service](client, context, cfg, account, region):
                        if item is not None:
                            yield item
                except Exception as exc:
                    safe = exc if isinstance(exc, IntegrationError) else map_aws_error(exc)
                    yield PartialFailure(
                        "metadata_collection", str(safe.code), f"{service}/{region}: collection failed", safe.retryable
                    )


class ConfiguredAwsDataPlatformProvider(AwsDataPlatformProvider):
    """Factory wrapper for composition that supplies validated provider data per execution."""
