from ..capabilities import AdapterCapabilities
from ..capabilities import CapabilityState as S
from ..contracts import MessagingSystem, ResourceKind
from .provider import ProviderAdapter


class PulsarAdapter(ProviderAdapter):
    system = MessagingSystem.PULSAR
    provider = "pulsar"
    resource_kinds = frozenset(
        {ResourceKind.NAMESPACE, ResourceKind.TOPIC, ResourceKind.PARTITION, ResourceKind.SUBSCRIPTION}
    )

    def capabilities(self):
        return AdapterCapabilities(
            provider=self.provider,
            messaging_system=self.system.value,
            state=S.NOT_IMPLEMENTED,
            inventory=S.NOT_IMPLEMENTED,
            limitations=["No authoritative production Pulsar collection source exists in this repository."],
        )


Adapter = PulsarAdapter
