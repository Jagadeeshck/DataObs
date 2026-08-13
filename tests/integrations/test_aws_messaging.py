import asyncio
import os
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from integrations.aws.cloudwatch import KINESIS_METRICS, SQS_METRICS, CloudWatchAdapter, metric_definition
from integrations.aws.configuration import parse_configuration
from integrations.aws.services import kinesis, sqs
from packages.collectors.sdk import EvidenceState, IntegrationContext, PartialFailure
from packages.streaming.adapters.kinesis import KinesisAdapter
from packages.streaming.adapters.provider import require_observation_envelope
from packages.streaming.adapters.sqs import SqsAdapter

CTX = IntegrationContext(
    "tenant", "integration", "run", datetime.max.replace(tzinfo=timezone.utc), attributes={"environment": "test"}
)
CFG = SimpleNamespace(raw={"service_options": {}, "cloudwatch": {"enabled": True}})


class MissingCloudWatch:
    def get_metric_data(self, **kwargs):
        return {"MetricDataResults": [{"Id": "m0", "Values": [0], "Timestamps": [datetime.now(timezone.utc)]}]}


def test_messaging_configuration_is_closed_and_bounded():
    parse_configuration(
        {
            "regions": ["eu-west-1"],
            "services": ["kinesis", "sqs"],
            "service_options": {
                "kinesis": {"maximum_streams": 1, "maximum_shard_pages": 1},
                "sqs": {"maximum_queues": 1},
            },
        }
    )
    with pytest.raises(Exception):
        parse_configuration(
            {"regions": ["eu-west-1"], "services": ["sqs"], "service_options": {"sqs": {"unknown": True}}}
        )
    with pytest.raises(Exception):
        parse_configuration(
            {
                "regions": ["eu-west-1"],
                "services": ["kinesis"],
                "service_options": {"kinesis": {"maximum_stream_pages": 101}},
            }
        )


def test_cloudwatch_allowlists_preserve_zero_and_missing():
    assert metric_definition("kinesis", "GetRecords.IteratorAgeMilliseconds")[0] == "AWS/Kinesis"
    assert metric_definition("sqs", "ApproximateAgeOfOldestMessage")[0] == "AWS/SQS"
    with pytest.raises(ValueError):
        metric_definition("sqs", "SecretMetric")
    values = CloudWatchAdapter(MissingCloudWatch()).collect(
        "id", "AWS/SQS", {"QueueName": "q"}, dict(list(SQS_METRICS.items())[:2])
    )
    assert values[0].value == 0 and values[0].state == EvidenceState.MEASURED
    assert values[1].value is None and values[1].state == EvidenceState.MISSING


def test_kinesis_bounded_inventory_topology_redaction_metrics_and_contract():
    class Client:
        called = []

        def __getattr__(self, name):
            if name in {"get_records", "get_shard_iterator", "subscribe_to_shard", "put_record", "put_records"}:
                raise AssertionError(name)
            raise AttributeError(name)

        def list_streams(self, **kwargs):
            self.called.append("list_streams")
            return {"StreamNames": ["safe"], "HasMoreStreams": True}

        def describe_stream_summary(self, **kwargs):
            self.called.append("describe_stream_summary")
            return {
                "StreamDescriptionSummary": {
                    "StreamARN": "arn:stream",
                    "StreamStatus": "ACTIVE",
                    "StreamModeDetails": {"StreamMode": "ON_DEMAND"},
                    "RetentionPeriodHours": 24,
                    "OpenShardCount": 1,
                    "ConsumerCount": 2,
                    "EncryptionType": "KMS",
                    "KeyId": "forbidden",
                    "EnhancedMonitoring": [{"ShardLevelMetrics": ["IncomingRecords"]}],
                }
            }

        def list_tags_for_stream(self, **kwargs):
            return {"Tags": [{"Key": "Owner", "Value": "team"}]}

        def list_shards(self, **kwargs):
            self.called.append("list_shards")
            return {
                "Shards": [
                    {
                        "ShardId": "shard-1",
                        "ParentShardId": "shard-0",
                        "HashKeyRange": {"StartingHashKey": "forbidden"},
                        "SequenceNumberRange": {"StartingSequenceNumber": "forbidden"},
                    }
                ],
                "NextToken": "more",
            }

    cfg = SimpleNamespace(
        raw={
            "service_options": {
                "kinesis": {
                    "maximum_streams": 1,
                    "maximum_stream_pages": 1,
                    "maximum_shards_per_stream": 1,
                    "maximum_shard_pages": 1,
                }
            },
            "cloudwatch": {},
        }
    )
    client = Client()
    values = list(kinesis.collect(client, CTX, cfg, "000000000000", "eu-west-1", cloudwatch_client=MissingCloudWatch()))
    resources = [v for v in values if hasattr(v, "source_evidence")]
    assert [v.resource_type for v in resources] == ["stream", "shard"]
    assert resources[0].source_evidence["stream_mode"] == "on_demand"
    assert resources[0].source_evidence["encrypted"] is True and resources[0].source_evidence["result_truncated"]
    assert resources[1].source_evidence["state"] == "open"
    assert "forbidden" not in repr(resources) and "KeyId" not in repr(resources)
    assert any(v.metric_name == "GetRecords.IteratorAgeMilliseconds" for v in values if hasattr(v, "metric_name"))
    envelope = dict(resources[0].source_evidence)
    require_observation_envelope(envelope)
    assert KinesisAdapter().resource(envelope).kinesis is None
    assert client.called == ["list_streams", "describe_stream_summary", "list_shards"]


def test_sqs_attribute_allowlist_dlq_approximate_redaction_metrics_and_contract():
    class Client:
        calls = []

        def __getattr__(self, name):
            if name in {"receive_message", "send_message", "delete_message", "purge_queue", "set_queue_attributes"}:
                raise AssertionError(name)
            raise AttributeError(name)

        def list_queues(self, **kwargs):
            return {
                "QueueUrls": [
                    "https://sqs.eu-west-1.amazonaws.com/0/source",
                    "https://sqs.eu-west-1.amazonaws.com/0/dlq",
                ]
            }

        def get_queue_attributes(self, **kwargs):
            assert (
                "All" not in kwargs["AttributeNames"]
                and "Policy" not in kwargs["AttributeNames"]
                and "KmsMasterKeyId" not in kwargs["AttributeNames"]
            )
            self.calls.append(tuple(kwargs["AttributeNames"]))
            name = kwargs["QueueUrl"].rsplit("/", 1)[-1]
            attrs = {
                "QueueArn": f"arn:{name}",
                "FifoQueue": "true",
                "MessageRetentionPeriod": "120",
                "ApproximateNumberOfMessages": "0",
                "ApproximateNumberOfMessagesNotVisible": "2",
                "ApproximateNumberOfMessagesDelayed": "1",
                "Policy": "forbidden",
                "KmsMasterKeyId": "forbidden",
            }
            if name == "source":
                attrs["RedrivePolicy"] = '{"deadLetterTargetArn":"arn:dlq","maxReceiveCount":"3","extra":"forbidden"}'
            return {"Attributes": attrs}

        def list_queue_tags(self, **kwargs):
            return {"Tags": {"Owner": "team"}}

    values = list(sqs.collect(Client(), CTX, CFG, "000000000000", "eu-west-1", cloudwatch_client=MissingCloudWatch()))
    resources = [v for v in values if hasattr(v, "source_evidence")]
    assert [v.resource_type for v in resources] == ["queue", "dead_letter_queue"]
    source = resources[0].source_evidence
    assert source["backlog_messages"] == 0 and source["measurement_method"] == "provider_approximate"
    assert source["dlq_relationship"] == {
        "source_queue": "arn:source",
        "dead_letter_queue": "arn:dlq",
        "max_receive_count": 3,
        "relationship_type": "redrive",
    }
    assert (
        "Policy" not in repr(resources) and "KmsMasterKeyId" not in repr(resources) and "extra" not in repr(resources)
    )
    envelope = dict(source)
    require_observation_envelope(envelope)
    assert SqsAdapter().resource(envelope).resource_kind == "queue"
    assert SqsAdapter().backlog(envelope).measurement_method == "provider_approximate"


def test_partial_permission_failure_preserves_siblings():
    class Client:
        def list_queues(self, **kwargs):
            return {"QueueUrls": ["https://x/bad", "https://x/good"]}

        def get_queue_attributes(self, QueueUrl, **kwargs):
            if QueueUrl.endswith("bad"):
                raise RuntimeError("raw secret provider error")
            return {"Attributes": {"QueueArn": "arn:good"}}

        def list_queue_tags(self, **kwargs):
            return {"Tags": {}}

    values = list(sqs.collect(Client(), CTX, CFG, "0", "eu-west-1"))
    assert isinstance(values[0], PartialFailure) and "raw secret" not in values[0].message
    assert values[1].native_resource_id == "arn:good"


@pytest.mark.skipif(
    os.getenv("RUN_AWS_KINESIS_INTEGRATION_TESTS") != "1", reason="opt-in disposable allowlist required"
)
def test_live_kinesis_read_only_placeholder():
    assert os.environ["AWS_KINESIS_STREAM_ALLOWLIST"]


@pytest.mark.skipif(os.getenv("RUN_AWS_SQS_INTEGRATION_TESTS") != "1", reason="opt-in disposable allowlist required")
def test_live_sqs_read_only_placeholder():
    assert os.environ["AWS_SQS_QUEUE_ALLOWLIST"]
