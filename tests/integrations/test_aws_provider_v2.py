from datetime import datetime, timezone
from types import SimpleNamespace

from integrations.aws.services import lambda_service, redshift, redshift_serverless, s3
from packages.collectors.sdk import IntegrationContext

CFG = SimpleNamespace(
    raw={
        "service_options": {
            "s3": {
                "include_buckets": ["synthetic"],
                "prefix_assets": [{"bucket": "synthetic", "prefix": "curated/"}],
                "maximum_prefix_samples": 1,
                "maximum_prefix_pages": 1,
            }
        }
    }
)
CTX = IntegrationContext("tenant", "integration", "run", datetime.now(timezone.utc))


def test_s3_collects_bounded_prefix_without_object_reads():
    class S3:
        calls = []

        def __getattr__(self, name):
            if name == "get_object":
                raise AssertionError("GetObject must never be used")

            def optional(**kwargs):
                self.calls.append(name)
                return {}

            return optional

        def list_buckets(self):
            return {"Buckets": [{"Name": "synthetic", "CreationDate": datetime.now(timezone.utc)}]}

        def get_bucket_location(self, **kwargs):
            return {"LocationConstraint": "eu-west-1"}

        def list_objects_v2(self, **kwargs):
            assert kwargs["MaxKeys"] == 1
            return {
                "Contents": [{"Key": "secret-token-value", "Size": 7, "LastModified": datetime.now(timezone.utc)}],
                "IsTruncated": True,
                "NextContinuationToken": "opaque",
            }

    client = S3()
    values = list(s3.collect(client, CTX, CFG, "000000000000", "eu-west-1"))
    assert [value.resource_type for value in values] == ["bucket", "prefix_asset"]
    assert values[1].source_evidence["sampled_object_count"] == 1
    assert values[1].source_evidence["sample_truncated"] is True
    assert "secret-token-value" not in repr(values)
    assert "get_object" not in client.calls


def test_lambda_uses_allowlist_and_omits_environment_and_reason():
    class Lambda:
        def list_functions(self, **kwargs):
            return {"Functions": [{"FunctionName": "data-platform-one", "FunctionArn": "arn:function"}]}

        def get_function_configuration(self, **kwargs):
            return {
                "FunctionName": "data-platform-one",
                "FunctionArn": "arn:function",
                "Runtime": "python3.13",
                "Environment": {"Variables": {"PASSWORD": "forbidden"}},
                "StateReason": "raw provider detail",
                "VpcConfig": {"VpcId": "vpc", "SubnetIds": ["forbidden"]},
            }

        def get_function_concurrency(self, **kwargs):
            return {"ReservedConcurrentExecutions": 2}

        def list_tags(self, **kwargs):
            return {"Tags": {}}

    cfg = SimpleNamespace(raw={"service_options": {"lambda": {"include_function_patterns": ["data-*"]}}})
    value = list(lambda_service.collect(Lambda(), CTX, cfg, "000000000000", "eu-west-1"))[0]
    rendered = repr(value.source_evidence)
    assert "Environment" not in rendered and "PASSWORD" not in rendered and "StateReason" not in rendered
    assert "SubnetIds" not in rendered


def test_redshift_inventory_omits_endpoint_username_and_sql_summary():
    class Redshift:
        def describe_clusters(self, **kwargs):
            return {
                "Clusters": [
                    {"ClusterIdentifier": "safe", "MasterUsername": "forbidden", "Endpoint": {"Address": "forbidden"}}
                ]
            }

    value = list(redshift.collect(Redshift(), CTX, SimpleNamespace(raw={}), "000000000000", "eu-west-1"))[0]
    assert "MasterUsername" not in repr(value) and "Endpoint" not in repr(value)
    summary = redshift.safe_query_summary({"Id": "q", "QueryString": "select forbidden", "DbUser": "alice"})
    assert "QueryString" not in summary and "alice" not in repr(summary)


def test_redshift_serverless_omits_endpoint_and_admin_username():
    class Client:
        def list_namespaces(self, **kwargs):
            return {"namespaces": [{"namespaceName": "n", "namespaceArn": "arn:n", "adminUsername": "forbidden"}]}

        def list_workgroups(self, **kwargs):
            return {
                "workgroups": [{"workgroupName": "w", "workgroupArn": "arn:w", "endpoint": {"address": "forbidden"}}]
            }

        def list_tags_for_resource(self, **kwargs):
            return {"tags": []}

    rendered = repr(
        list(redshift_serverless.collect(Client(), CTX, SimpleNamespace(raw={}), "000000000000", "eu-west-1"))
    )
    assert "adminUsername" not in rendered and "endpoint" not in rendered and "forbidden" not in rendered
