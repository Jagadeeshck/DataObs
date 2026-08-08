from .azure_messaging import EventHubsAdapter, ServiceBusAdapter
from .kafka import KafkaAdapter
from .kinesis import KinesisAdapter
from .pubsub import PubSubAdapter
from .pulsar import PulsarAdapter
from .rabbitmq import RabbitMqAdapter
from .sqs import SqsAdapter

ADAPTERS = {
    "kafka": KafkaAdapter,
    "kinesis": KinesisAdapter,
    "sqs": SqsAdapter,
    "rabbitmq": RabbitMqAdapter,
    "google_pubsub": PubSubAdapter,
    "azure_event_hubs": EventHubsAdapter,
    "azure_service_bus": ServiceBusAdapter,
    "pulsar": PulsarAdapter,
}


def get_adapter(messaging_system: str):
    try:
        return ADAPTERS[messaging_system]()
    except KeyError as exc:
        raise ValueError("unsupported messaging system") from exc


__all__ = ["ADAPTERS", "get_adapter"]
