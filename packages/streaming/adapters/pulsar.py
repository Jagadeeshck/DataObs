from ..capabilities import AdapterCapabilities, CapabilityState


class Adapter:
    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            provider="pulsar",
            state=CapabilityState.NOT_IMPLEMENTED,
            inventory=CapabilityState.NOT_IMPLEMENTED,
            offsets=CapabilityState.NOT_IMPLEMENTED,
            groups=CapabilityState.NOT_IMPLEMENTED,
        )
