from urllib.parse import urlparse

from pydantic import BaseModel, field_validator


class AirflowConfig(BaseModel):
    base_url: str
    secret_ref: str
    verify_tls: bool = True
    allowed_dags: set[str] = set()
    allowed_config_keys: set[str] = set()

    @field_validator("base_url")
    @classmethod
    def safe_url(cls, v):
        p = urlparse(v)
        if p.scheme != "https" and p.hostname not in {"localhost", "airflow"}:
            raise ValueError("Airflow URL must use TLS")
        if p.username or p.password or not p.hostname:
            raise ValueError("Airflow URL must not contain credentials")
        return v.rstrip("/")
