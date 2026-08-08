from ..capabilities import AdapterCapabilities
from ..capabilities import CapabilityState as S
from ..contracts import MessagingSystem, ResourceKind
from .provider import ProviderAdapter


class PubSubAdapter(ProviderAdapter):
    system = MessagingSystem.GOOGLE_PUBSUB
    provider = "gcp"
    resource_kinds = frozenset({ResourceKind.TOPIC, ResourceKind.SUBSCRIPTION, ResourceKind.DEAD_LETTER_TOPIC})

    def capabilities(self):
        return AdapterCapabilities(
            provider=self.provider,
            messaging_system=self.system.value,
            state=S.NOT_CONFIGURED,
            inventory=S.NOT_CONFIGURED,
            topology=S.PARTIAL,
            throughput=S.NOT_CONFIGURED,
            backlog_count=S.NOT_CONFIGURED,
            backlog_age=S.NOT_CONFIGURED,
            subscriptions=S.NOT_CONFIGURED,
            retention=S.NOT_CONFIGURED,
            dead_letter=S.NOT_CONFIGURED,
            otel_trace_correlation=S.PARTIAL,
            offsets=S.UNSUPPORTED,
            consumer_groups=S.UNSUPPORTED,
            partitions=S.UNSUPPORTED,
            limitations=["Subscriptions remain distinct resources; runtime monitoring evidence is not configured."],
        )


Adapter = PubSubAdapter
