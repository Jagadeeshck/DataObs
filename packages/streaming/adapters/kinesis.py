from ..capabilities import AdapterCapabilities
from ..capabilities import CapabilityState as S
from ..contracts import MessagingSystem, ResourceKind
from .provider import ProviderAdapter


class KinesisAdapter(ProviderAdapter):
    system = MessagingSystem.KINESIS
    provider = "aws"
    resource_kinds = frozenset({ResourceKind.STREAM, ResourceKind.SHARD})

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            provider=self.provider,
            messaging_system=self.system.value,
            state=S.PARTIAL,
            inventory=S.AVAILABLE,
            topology=S.AVAILABLE,
            throughput=S.AVAILABLE,
            byte_throughput=S.AVAILABLE,
            backlog_age=S.AVAILABLE,
            shards=S.AVAILABLE,
            retention=S.AVAILABLE,
            availability=S.AVAILABLE,
            producer_identity=S.PARTIAL,
            consumer_identity=S.PARTIAL,
            otel_trace_correlation=S.PARTIAL,
            limitations=[
                "Runtime collection depends on configured AWS/Elastic evidence; committed offsets do not exist."
            ],
        )


Adapter = KinesisAdapter
