from ..capabilities import AdapterCapabilities
from ..capabilities import CapabilityState as S
from ..contracts import MessagingSystem, ResourceKind
from .provider import ProviderAdapter


class KafkaAdapter(ProviderAdapter):
    system = MessagingSystem.KAFKA
    provider = "kafka"
    resource_kinds = frozenset(
        {
            ResourceKind.NAMESPACE,
            ResourceKind.BROKER,
            ResourceKind.TOPIC,
            ResourceKind.PARTITION,
            ResourceKind.CONSUMER_GROUP,
            ResourceKind.CONNECTOR,
            ResourceKind.DEAD_LETTER_TOPIC,
        }
    )

    def capabilities(self):
        return AdapterCapabilities(
            provider=self.provider,
            messaging_system=self.system.value,
            state=S.AVAILABLE,
            inventory=S.AVAILABLE,
            topology=S.AVAILABLE,
            throughput=S.AVAILABLE,
            byte_throughput=S.AVAILABLE,
            backlog_count=S.AVAILABLE,
            backlog_age=S.PARTIAL,
            offsets=S.AVAILABLE,
            consumer_groups=S.AVAILABLE,
            partitions=S.AVAILABLE,
            retention=S.AVAILABLE,
            replication=S.AVAILABLE,
            availability=S.AVAILABLE,
            dead_letter=S.PARTIAL,
            schemas=S.AVAILABLE,
            connectors=S.AVAILABLE,
            producer_identity=S.PARTIAL,
            consumer_identity=S.PARTIAL,
            otel_trace_correlation=S.PARTIAL,
        )
