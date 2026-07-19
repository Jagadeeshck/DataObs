from pydantic import BaseModel, Field, HttpUrl


class KafkaConnectConfig(BaseModel):
    base_url: HttpUrl
    timeout_seconds: float = Field(default=5, gt=0, le=30)
    allowed_hosts: set[str]
