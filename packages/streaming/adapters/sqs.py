from ..capabilities import AdapterCapabilities, CapabilityState


class Adapter:
    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            provider="sqs",
            state=CapabilityState.NOT_IMPLEMENTED,
            inventory=CapabilityState.NOT_IMPLEMENTED,
            offsets=CapabilityState.NOT_IMPLEMENTED,
            groups=CapabilityState.NOT_IMPLEMENTED,
        )
