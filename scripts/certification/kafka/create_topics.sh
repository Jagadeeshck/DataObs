#!/usr/bin/env bash
set -Eeuo pipefail
kafka-topics.sh --bootstrap-server "${KAFKA_BOOTSTRAP_SERVERS}" --create --if-not-exists --topic certification-orders --partitions 3 --replication-factor 3
