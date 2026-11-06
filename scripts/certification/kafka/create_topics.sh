#!/usr/bin/env bash
set -Eeuo pipefail

python3 - <<'PYEOF'
import os
import sys
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaException

bootstrap = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
admin = AdminClient({"bootstrap.servers": bootstrap})

topic_name = "certification-orders"
new_topic = NewTopic(topic_name, num_partitions=3, replication_factor=3)

futures = admin.create_topics([new_topic])
for topic, future in futures.items():
    try:
        future.result()
        print(f"Topic '{topic}' created successfully.")
    except KafkaException as exc:
        err = exc.args[0]
        # TOPIC_ALREADY_EXISTS (error code 36) is treated as success
        if err.code() == 36:
            print(f"Topic '{topic}' already exists — OK.")
        else:
            print(f"ERROR creating topic '{topic}': {exc}", file=sys.stderr)
            sys.exit(1)
PYEOF
