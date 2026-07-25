import os


class KafkaClient:
    def admin(self):
        from confluent_kafka.admin import AdminClient

        return AdminClient(
            {"bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:19092"), "socket.timeout.ms": 10000}
        )
