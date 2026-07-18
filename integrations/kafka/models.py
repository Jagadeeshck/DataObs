from __future__ import annotations

from typing import Any

from pydantic import Field

from packages.pathways.models import CommonModel


class KafkaCluster(CommonModel):
    name: str
    controller_id: int | None = None
    broker_count: int = 0


class KafkaBroker(CommonModel):
    broker_id: int
    host: str
    port: int
    rack: str | None = None
    controller: bool = False


class KafkaTopic(CommonModel):
    topic_id: str
    name: str
    partition_count: int
    replication_factor: int


class KafkaPartition(CommonModel):
    topic_id: str
    partition: int
    leader_id: int | None = None
    replicas: list[int] = Field(default_factory=list)
    isr: list[int] = Field(default_factory=list)
    earliest_offset: int | None = None
    latest_offset: int | None = None


class KafkaConsumerMember(CommonModel):
    group_id: str
    member_id: str
    client_id: str | None = None
    assignments: list[str] = Field(default_factory=list)


class KafkaConsumerGroup(CommonModel):
    group_name: str
    state: str
    members: list[KafkaConsumerMember] = Field(default_factory=list)


class KafkaProducerService(CommonModel):
    pass


class KafkaConsumerService(CommonModel):
    pass


class KafkaConnectCluster(CommonModel):
    base_url: str


class KafkaConnector(CommonModel):
    name: str
    connector_type: str
    state: str
    config_fingerprint: str


class KafkaConnectorTask(CommonModel):
    connector_id: str
    task_id: int
    state: str


class KafkaSchemaSubject(CommonModel):
    subject: str
    compatibility: str | None = None


class KafkaSchemaVersion(CommonModel):
    subject_id: str
    version: int
    schema_fingerprint: str


class KafkaConfigurationSnapshot(CommonModel):
    resource_type: str
    resource_id: str
    fingerprint: str
    values: dict[str, Any] = Field(default_factory=dict)


class KafkaChangeEvent(CommonModel):
    resource_type: str
    resource_id: str
    changes: dict[str, Any] = Field(default_factory=dict)
