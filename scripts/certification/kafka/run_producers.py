import json
import os

from confluent_kafka import Producer

p = Producer({"bootstrap.servers": os.environ["KAFKA_BOOTSTRAP_SERVERS"]})
for i in range(20):
    p.produce("certification-orders", key=str(i), value=json.dumps({"id": f"order-{i:03d}"}))
p.flush(10)
