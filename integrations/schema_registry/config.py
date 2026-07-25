from pydantic import BaseModel, Field, HttpUrl


class SchemaRegistryConfig(BaseModel):
    base_url: HttpUrl
    allowed_hosts: set[str]
    timeout_seconds: float = Field(default=5, gt=0, le=30)
