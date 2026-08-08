from ..capabilities import AdapterCapabilities
from ..capabilities import CapabilityState as S
from ..contracts import MessagingSystem, ResourceKind
from .provider import ProviderAdapter


class SqsAdapter(ProviderAdapter):
    system = MessagingSystem.SQS
    provider = "aws"
    resource_kinds = frozenset({ResourceKind.QUEUE, ResourceKind.DEAD_LETTER_QUEUE})

    def backlog(self, observation, **kwargs):
        return super().backlog(
            observation, approximate=True, provider_metric="ApproximateNumberOfMessagesVisible", **kwargs
        )

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            provider=self.provider,
            messaging_system=self.system.value,
            state=S.PARTIAL,
            inventory=S.AVAILABLE,
            topology=S.AVAILABLE,
            throughput=S.AVAILABLE,
            backlog_count=S.AVAILABLE,
            backlog_age=S.AVAILABLE,
            retention=S.AVAILABLE,
            availability=S.AVAILABLE,
            dead_letter=S.AVAILABLE,
            producer_identity=S.PARTIAL,
            consumer_identity=S.PARTIAL,
            otel_trace_correlation=S.PARTIAL,
            offsets=S.UNSUPPORTED,
            consumer_groups=S.UNSUPPORTED,
            partitions=S.UNSUPPORTED,
            shards=S.UNSUPPORTED,
            limitations=["Queue counts are provider-approximate; SQS has no offsets or consumer groups."],
        )


Adapter = SqsAdapter
