from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class KafkaSecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    protocol: str = "PLAINTEXT"
    sasl_mechanism: str | None = None
    username_ref: str | None = None
    password_ref: str | None = None
    ca_file: str | None = None
    certificate_file: str | None = None
    key_file: str | None = None
    verify_tls: bool = True

    @field_validator("protocol")
    @classmethod
    def protocol_allowed(cls, value: str) -> str:
        if value not in {"PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"}:
            raise ValueError("unsupported security protocol")
        return value

    @field_validator("sasl_mechanism")
    @classmethod
    def mechanism_allowed(cls, value: str | None) -> str | None:
        if value not in {None, "PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"}:
            raise ValueError("unsupported SASL mechanism")
        return value

    @model_validator(mode="after")
    def coherent_security(self) -> "KafkaSecurityConfig":
        if self.protocol == "SASL_SSL" and not self.sasl_mechanism:
            raise ValueError("SASL_SSL requires a supported SASL mechanism")
        if self.sasl_mechanism and (not self.username_ref or not self.password_ref):
            raise ValueError("SASL requires username_ref and password_ref")
        for value in (self.username_ref, self.password_ref):
            if value and not value.startswith(("env:", "file:")):
                raise ValueError("credentials must use env: or file: references")
        if self.protocol in {"SSL", "SASL_SSL"} and not self.verify_tls:
            raise ValueError("TLS verification cannot be disabled")
        return self


class KafkaObserverConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: str
    environment: str
    integration_id: str
    bootstrap_servers: list[str]
    client_id: str = "dataobs-kafka-observer"
    request_timeout_seconds: float = Field(default=10, gt=0, le=120)
    retries: int = Field(default=3, ge=0, le=10)
    backoff_seconds: float = Field(default=1, ge=0.1, le=60)
    concurrency: int = Field(default=4, ge=1, le=32)
    optional_read_enabled: bool = False
    bootstrap_server_allowlist: list[str] = Field(default_factory=list)
    topic_include: list[str] = Field(default_factory=lambda: [".*"])
    topic_exclude: list[str] = Field(default_factory=lambda: ["^__.*"])
    group_include: list[str] = Field(default_factory=lambda: [".*"])
    group_exclude: list[str] = Field(default_factory=list)
    include_internal_topics: bool = False
    batch_size: int = Field(default=500, ge=1, le=10_000)
    maximum_combinations_per_cycle: int = Field(default=100_000, ge=1, le=1_000_000)
    lease_duration_seconds: float = Field(default=60, ge=10, le=3600)
    lease_renewal_seconds: float = Field(default=20, ge=1, le=1200)
    inventory_interval_seconds: float = Field(default=300, ge=5)
    group_interval_seconds: float = Field(default=30, ge=5)
    offset_interval_seconds: float = Field(default=30, ge=5)
    connect_interval_seconds: float = Field(default=60, ge=5)
    schema_interval_seconds: float = Field(default=300, ge=5)
    metric_interval_seconds: float = Field(default=30, ge=5)
    kafka_connect_url: str | None = None
    kafka_connect_allowed_hosts: set[str] = Field(default_factory=set)
    schema_registry_url: str | None = None
    schema_registry_allowed_hosts: set[str] = Field(default_factory=set)
    maximum_connectors: int = Field(default=1000, ge=1, le=10_000)
    maximum_subjects: int = Field(default=1000, ge=1, le=10_000)
    maximum_schema_versions: int = Field(default=100, ge=1, le=1000)
    security: KafkaSecurityConfig = Field(default_factory=KafkaSecurityConfig)

    @field_validator("bootstrap_servers")
    @classmethod
    def safe_bootstrap_servers(cls, values: list[str]) -> list[str]:
        if not values or any(not re.fullmatch(r"[A-Za-z0-9._-]+:\d{1,5}", value) for value in values):
            raise ValueError("bootstrap_servers must contain host:port entries without credentials or URLs")
        return values

    @model_validator(mode="after")
    def allowed_bootstrap_servers(self) -> "KafkaObserverConfig":
        if self.bootstrap_server_allowlist and not set(self.bootstrap_servers) <= set(self.bootstrap_server_allowlist):
            raise ValueError("bootstrap server is not allowlisted")
        if self.lease_renewal_seconds >= self.lease_duration_seconds:
            raise ValueError("lease renewal must occur before lease expiry")
        if bool(self.kafka_connect_url) != bool(self.kafka_connect_allowed_hosts):
            raise ValueError("Kafka Connect URL and allowed hosts must be configured together")
        if bool(self.schema_registry_url) != bool(self.schema_registry_allowed_hosts):
            raise ValueError("Schema Registry URL and allowed hosts must be configured together")
        return self
