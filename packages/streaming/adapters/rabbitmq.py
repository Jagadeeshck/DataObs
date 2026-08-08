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
            state=S.NOT_CONFIGURED,
            inventory=S.NOT_CONFIGURED,
            topology=S.NOT_CONFIGURED,
            throughput=S.NOT_CONFIGURED,
            backlog_count=S.NOT_CONFIGURED,
            dead_letter=S.NOT_CONFIGURED,
            redelivery=S.NOT_CONFIGURED,
            consumer_identity=S.PARTIAL,
            producer_identity=S.PARTIAL,
            otel_trace_correlation=S.PARTIAL,
            offsets=S.UNSUPPORTED,
            consumer_groups=S.UNSUPPORTED,
            partitions=S.UNSUPPORTED,
            limitations=["Requires the read-only RabbitMQ management/Elastic integration."],
        )


Adapter = RabbitMqAdapter
