# Kafka DSM demo

Run `docker compose -f docker-compose.kafka-dsm-demo.yml --profile ci up -d --build`, apply Elasticsearch migrations with `./bin/dataobs elastic apply`, and run `./scripts/demo_kafka_dsm.sh`. The CI profile supplies three KRaft brokers. This initial harness validates configuration; the real Elasticsearch/Kibana end-to-end job remains required before the PR leaves draft.
