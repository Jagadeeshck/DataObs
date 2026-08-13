from ..capabilities import AdapterCapabilities
from ..capabilities import CapabilityState as S
from ..contracts import MessagingSystem, ResourceKind
from .provider import ProviderAdapter


class RabbitMqAdapter(ProviderAdapter):
    system = MessagingSystem.RABBITMQ
    provider = "rabbitmq"
    resource_kinds = frozenset(
        {ResourceKind.NAMESPACE, ResourceKind.EXCHANGE, ResourceKind.QUEUE, ResourceKind.DEAD_LETTER_QUEUE}
    )

    def capabilities(self):
        return AdapterCapabilities(
            provider=self.provider,
            messaging_system=self.system.value,
            state=S.PARTIAL,
            inventory=S.FUNCTIONAL,
            topology=S.FUNCTIONAL,
            throughput=S.PARTIAL,
            backlog_count=S.FUNCTIONAL,
            availability=S.PARTIAL,
            dead_letter=S.PARTIAL,
            redelivery=S.PARTIAL,
            consumer_identity=S.PARTIAL,
            producer_identity=S.PARTIAL,
            otel_trace_correlation=S.PARTIAL,
            offsets=S.UNSUPPORTED,
            consumer_groups=S.UNSUPPORTED,
            partitions=S.UNSUPPORTED,
            limitations=["Management HTTP API v1 is functional-unvalidated; optional statistics and hosted validation remain partial."],
        )


Adapter = RabbitMqAdapter
