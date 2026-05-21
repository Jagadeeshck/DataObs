from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import yaml

logger = logging.getLogger(__name__)
EnvironmentMode = Literal["development", "test", "poc", "production"]


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class RuntimeSettings:
    env: EnvironmentMode = "development"
    config_path: str | None = None
    allow_memory_store_in_production: bool = False


@dataclass(frozen=True)
class APISettings:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass(frozen=True)
class ElasticsearchSettings:
    url: str | None = "http://localhost:9200"
    user: str = "elastic"
    password: str = ""
    api_key: str | None = None
    verify_tls: bool = True

    @property
    def host_for_logs(self) -> str:
        if not self.url:
            return "<unset>"
        parsed = urlsplit(self.url)
        return parsed.netloc or parsed.path


@dataclass(frozen=True)
class AuthSettings:
    api_token: str | None = None
    allow_unauthenticated_dev: bool = True
    provider: str = "token"


@dataclass(frozen=True)
class TenantSettings:
    tenant_id: str = "default"


@dataclass(frozen=True)
class ObservabilitySettings:
    log_level: str = "INFO"


@dataclass(frozen=True)
class AppSettings:
    runtime: RuntimeSettings
    api: APISettings
    elasticsearch: ElasticsearchSettings
    auth: AuthSettings
    tenant: TenantSettings
    observability: ObservabilitySettings
    store_backend: str = "memory"

    @property
    def api_token(self) -> str | None:
        return self.auth.api_token

    @property
    def host(self) -> str:
        return self.api.host

    @property
    def port(self) -> int:
        return self.api.port

    @property
    def tenant_id(self) -> str:
        return self.tenant.tenant_id

    @property
    def log_level(self) -> str:
        return self.observability.log_level

    @property
    def allow_unauthenticated_dev(self) -> bool:
        return self.auth.allow_unauthenticated_dev

    @property
    def auth_mode(self) -> str:
        if self.api_token:
            return "bearer"
        return "development-unauthenticated" if self.auth.allow_unauthenticated_dev else "required"


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_get(d: dict[str, Any], *path: str, default: Any = None) -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def load_settings() -> AppSettings:
    env = os.getenv("DATAOBS_ENV", "development").strip().lower()
    if env not in {"development", "test", "poc", "production"}:
        raise ConfigurationError("DATAOBS_ENV must be one of development|test|poc|production")

    explicit_cfg = os.getenv("DATAOBS_CONFIG")
    default_cfg = Path("config/dataobs_poc.yaml") if env == "poc" else Path("config/dataobs.yaml")
    config_path = Path(explicit_cfg) if explicit_cfg else default_cfg
    config = _load_yaml(config_path)

    settings = AppSettings(
        runtime=RuntimeSettings(
            env=env,
            config_path=str(config_path) if config_path.exists() else None,
            allow_memory_store_in_production=_to_bool(os.getenv("DATAOBS_ALLOW_MEMORY_STORE_IN_PRODUCTION", False)),
        ),
        api=APISettings(
            host=os.getenv("API_HOST", str(_deep_get(config, "api", "host", default="0.0.0.0"))),
            port=int(os.getenv("API_PORT", _deep_get(config, "api", "port", default=8080))),
        ),
        elasticsearch=ElasticsearchSettings(
            url=os.getenv("ELASTICSEARCH_URL", _deep_get(config, "elasticsearch", "url", default="http://localhost:9200")),
            user=os.getenv("ELASTICSEARCH_USER", _deep_get(config, "elasticsearch", "user", default="elastic")),
            password=os.getenv("ELASTICSEARCH_PASSWORD", _deep_get(config, "elasticsearch", "password", default="")),
            api_key=os.getenv("ELASTICSEARCH_API_KEY", _deep_get(config, "elasticsearch", "api_key", default=None)),
            verify_tls=_to_bool(os.getenv("ELASTICSEARCH_VERIFY_TLS", _deep_get(config, "elasticsearch", "verify_tls", default=True)), default=True),
        ),
        auth=AuthSettings(
            api_token=os.getenv("API_TOKEN", _deep_get(config, "auth", "api_token", default=None)) or None,
            allow_unauthenticated_dev=_to_bool(os.getenv("DATAOBS_ALLOW_UNAUTHENTICATED_DEV", _deep_get(config, "auth", "allow_unauthenticated_dev", default=True)), default=True),
        ),
        tenant=TenantSettings(tenant_id=str(os.getenv("DATAOBS_TENANT_ID", _deep_get(config, "tenant", "id", default="default")))),
        observability=ObservabilitySettings(log_level=str(os.getenv("LOG_LEVEL", _deep_get(config, "observability", "log_level", default="INFO"))).upper()),
        store_backend=str(os.getenv("DATAOBS_STORE_BACKEND", _deep_get(config, "store", "backend", default="memory"))).lower(),
    )

    _validate(settings)
    logger.info("DataObs settings loaded env=%s backend=%s tenant=%s es_host=%s", settings.runtime.env, settings.store_backend, settings.tenant_id, settings.elasticsearch.host_for_logs)
    return settings


def _validate(settings: AppSettings) -> None:
    banned = {"changeme", "dataobs_poc_elastic", "dataobs_poc_kibana"}
    if settings.runtime.env == "production":
        if not settings.auth.api_token:
            raise ConfigurationError("Production requires API_TOKEN or stronger auth provider.")
        if settings.auth.allow_unauthenticated_dev:
            raise ConfigurationError("Production forbids unauthenticated dev mode.")
        if settings.store_backend == "memory" and not settings.runtime.allow_memory_store_in_production:
            raise ConfigurationError("Production forbids DATAOBS_STORE_BACKEND=memory.")
        if not settings.elasticsearch.url:
            raise ConfigurationError("Production requires ELASTICSEARCH_URL.")
        if not (settings.elasticsearch.api_key or (settings.elasticsearch.user and settings.elasticsearch.password)):
            raise ConfigurationError("Production requires Elasticsearch credentials or API key.")
        if settings.elasticsearch.password and settings.elasticsearch.password.lower() in banned:
            raise ConfigurationError("Production forbids default/changeme Elasticsearch passwords.")
        if settings.tenant_id == "default":
            raise ConfigurationError("Production requires explicit DATAOBS_TENANT_ID.")
        if not settings.elasticsearch.verify_tls:
            raise ConfigurationError("Production requires TLS verification.")

    if settings.runtime.env in {"development", "poc", "test"} and not settings.elasticsearch.verify_tls:
        logger.warning("ELASTICSEARCH_VERIFY_TLS=false in %s mode.", settings.runtime.env)
