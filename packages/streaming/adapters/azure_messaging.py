from ..capabilities import AdapterCapabilities
from ..capabilities import CapabilityState as S
from ..contracts import MessagingSystem, ResourceKind
from .provider import ProviderAdapter


class EventHubsAdapter(ProviderAdapter):
    system = MessagingSystem.AZURE_EVENT_HUBS
    provider = "azure"
    resource_kinds = frozenset(
        {ResourceKind.NAMESPACE, ResourceKind.STREAM, ResourceKind.PARTITION, ResourceKind.CONSUMER_GROUP}
    )

    def capabilities(self):
        return AdapterCapabilities(
            provider=self.provider,
            messaging_system=self.system.value,
            state=S.NOT_CONFIGURED,
            inventory=S.NOT_CONFIGURED,
            topology=S.NOT_CONFIGURED,
            throughput=S.NOT_CONFIGURED,
            byte_throughput=S.NOT_CONFIGURED,
            partitions=S.NOT_CONFIGURED,
            consumer_groups=S.NOT_CONFIGURED,
            retention=S.NOT_CONFIGURED,
            availability=S.NOT_CONFIGURED,
            offsets=S.PARTIAL,
            limitations=["Lag is unavailable unless checkpoint/sequence evidence is collected."],
        )


class ServiceBusAdapter(ProviderAdapter):
    system = MessagingSystem.AZURE_SERVICE_BUS
    provider = "azure"
    resource_kinds = frozenset(
        {
            ResourceKind.NAMESPACE,
            ResourceKind.QUEUE,
            ResourceKind.TOPIC,
            ResourceKind.SUBSCRIPTION,
            ResourceKind.DEAD_LETTER_QUEUE,
        }
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
            subscriptions=S.NOT_CONFIGURED,
            dead_letter=S.NOT_CONFIGURED,
            offsets=S.UNSUPPORTED,
            consumer_groups=S.UNSUPPORTED,
            partitions=S.UNSUPPORTED,
            limitations=["Service Bus does not expose Event Hubs partition semantics."],
        )


Adapter = EventHubsAdapter
