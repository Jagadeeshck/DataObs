from ..capabilities import AdapterCapabilities, CapabilityState


class KafkaAdapter:
    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            provider="kafka",
            state=CapabilityState.AVAILABLE,
            inventory=CapabilityState.AVAILABLE,
            offsets=CapabilityState.AVAILABLE,
            groups=CapabilityState.AVAILABLE,
        )
