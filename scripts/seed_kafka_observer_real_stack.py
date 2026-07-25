#!/usr/bin/env python3
"""Create deterministic, payload-free Kafka Observer metadata fixtures."""

import json
import subprocess

BROKER = "kafka-1:9092"
TOPICS = ("shared.orders", "shared.compacted", "shared.dlq")
for topic in TOPICS:
    command = [
        "docker",
        "compose",
        "-f",
        "docker-compose.kafka-observer-real-stack.yml",
        "exec",
        "-T",
        "kafka-1",
        "kafka-topics.sh",
        "--bootstrap-server",
        BROKER,
        "--create",
        "--if-not-exists",
        "--topic",
        topic,
        "--partitions",
        "3",
        "--replication-factor",
        "3",
    ]
    if topic.endswith("compacted"):
        command += ["--config", "cleanup.policy=compact"]
    subprocess.run(command, check=True)
print(json.dumps({"tenants": ["tenant-a", "tenant-b"], "topics": TOPICS, "payloads_persisted": False}))
