import os

from confluent_kafka import Consumer

c = Consumer(
    {
        "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP_SERVERS"],
        "group.id": "certification-healthy",
        "auto.offset.reset": "earliest",
    }
)
c.subscribe(["certification-orders"])
for _ in range(20):
    c.poll(1)
c.commit()
c.close()
