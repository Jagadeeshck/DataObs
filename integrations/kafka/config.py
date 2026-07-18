from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KafkaSecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    protocol: str = "PLAINTEXT"
    sasl_mechanism: str | None = None
    username_ref: str | None = None
    password_ref: str | None = None
    ca_file: str | None = None
    certificate_file: str | None = None
    key_file: str | None = None

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
    security: KafkaSecurityConfig = Field(default_factory=KafkaSecurityConfig)
