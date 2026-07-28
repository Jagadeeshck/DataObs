from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
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
    allow_unauthenticated_dev: bool = False
    provider: str = "local"
    oidc: "OIDCSettings" = field(default_factory=lambda: OIDCSettings())


@dataclass(frozen=True)
class OIDCSettings:
    issuer: str = ""
    audience: str = ""
    jwks_url: str | None = None
    allowed_algorithms: tuple[str, ...] = ("RS256",)
    client_id: str = ""
    subject_claim: str = "sub"
    username_claim: str = "preferred_username"
    groups_claim: str = "groups"
    tenants_claim: str = "dataobs_access"
    environments_claim: str = "environments"
    roles_claim: str = "dataobs_roles"
    clock_skew_seconds: int = 30
    discovery_timeout_seconds: float = 5.0
    jwks_cache_ttl_seconds: int = 300
    required_scopes: tuple[str, ...] = ()
    platform_admin_groups: frozenset[str] = frozenset()
    group_role_mappings: dict[str, tuple[str, ...]] = field(default_factory=dict)
    maximum_token_bytes: int = 16384


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


def _structured(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list, tuple)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return [item.strip() for item in str(value).split(",") if item.strip()]


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
            url=os.getenv(
                "ELASTICSEARCH_URL", _deep_get(config, "elasticsearch", "url", default="http://localhost:9200")
            ),
            user=os.getenv("ELASTICSEARCH_USER", _deep_get(config, "elasticsearch", "user", default="elastic")),
            password=os.getenv("ELASTICSEARCH_PASSWORD", _deep_get(config, "elasticsearch", "password", default="")),
            api_key=os.getenv("ELASTICSEARCH_API_KEY", _deep_get(config, "elasticsearch", "api_key", default=None)),
            verify_tls=_to_bool(
                os.getenv("ELASTICSEARCH_VERIFY_TLS", _deep_get(config, "elasticsearch", "verify_tls", default=True)),
                default=True,
            ),
        ),
        auth=AuthSettings(
            api_token=os.getenv("API_TOKEN", _deep_get(config, "auth", "api_token", default=None)) or None,
            allow_unauthenticated_dev=_to_bool(
                os.getenv(
                    "DATAOBS_ALLOW_UNAUTHENTICATED_DEV",
                    _deep_get(config, "auth", "allow_unauthenticated_dev", default=False),
                ),
                default=False,
            ),
            provider=str(os.getenv("DATAOBS_AUTH_PROVIDER", _deep_get(config, "auth", "provider", default="local"))),
            oidc=OIDCSettings(
                issuer=str(
                    os.getenv("DATAOBS_OIDC_ISSUER", _deep_get(config, "auth", "oidc", "issuer", default=""))
                ).rstrip("/"),
                audience=str(
                    os.getenv("DATAOBS_OIDC_AUDIENCE", _deep_get(config, "auth", "oidc", "audience", default=""))
                ),
                jwks_url=os.getenv(
                    "DATAOBS_OIDC_JWKS_URL", _deep_get(config, "auth", "oidc", "jwks_url", default=None)
                ),
                allowed_algorithms=tuple(
                    _structured(
                        os.getenv(
                            "DATAOBS_OIDC_ALLOWED_ALGORITHMS",
                            _deep_get(config, "auth", "oidc", "allowed_algorithms", default=["RS256"]),
                        ),
                        ["RS256"],
                    )
                ),
                client_id=str(
                    os.getenv("DATAOBS_OIDC_CLIENT_ID", _deep_get(config, "auth", "oidc", "client_id", default=""))
                ),
                subject_claim=str(os.getenv("DATAOBS_OIDC_SUBJECT_CLAIM", "sub")),
                username_claim=str(os.getenv("DATAOBS_OIDC_USERNAME_CLAIM", "preferred_username")),
                groups_claim=str(os.getenv("DATAOBS_OIDC_GROUPS_CLAIM", "groups")),
                tenants_claim=str(os.getenv("DATAOBS_OIDC_TENANTS_CLAIM", "dataobs_access")),
                environments_claim=str(os.getenv("DATAOBS_OIDC_ENVIRONMENTS_CLAIM", "environments")),
                roles_claim=str(os.getenv("DATAOBS_OIDC_ROLES_CLAIM", "dataobs_roles")),
                clock_skew_seconds=int(os.getenv("DATAOBS_OIDC_CLOCK_SKEW_SECONDS", "30")),
                discovery_timeout_seconds=float(os.getenv("DATAOBS_OIDC_DISCOVERY_TIMEOUT_SECONDS", "5")),
                jwks_cache_ttl_seconds=int(os.getenv("DATAOBS_OIDC_JWKS_CACHE_TTL_SECONDS", "300")),
                required_scopes=tuple(
                    _structured(
                        os.getenv(
                            "DATAOBS_OIDC_REQUIRED_SCOPES",
                            _deep_get(config, "auth", "oidc", "required_scopes", default=[]),
                        ),
                        [],
                    )
                ),
                platform_admin_groups=frozenset(
                    _structured(
                        os.getenv(
                            "DATAOBS_OIDC_PLATFORM_ADMIN_GROUPS",
                            _deep_get(config, "auth", "oidc", "platform_admin_groups", default=[]),
                        ),
                        [],
                    )
                ),
                group_role_mappings={
                    str(k): tuple(v)
                    for k, v in _structured(
                        os.getenv(
                            "DATAOBS_OIDC_GROUP_ROLE_MAPPINGS",
                            _deep_get(config, "auth", "oidc", "group_role_mappings", default={}),
                        ),
                        {},
                    ).items()
                },
            ),
        ),
        tenant=TenantSettings(
            tenant_id=str(os.getenv("DATAOBS_TENANT_ID", _deep_get(config, "tenant", "id", default="default")))
        ),
        observability=ObservabilitySettings(
            log_level=str(
                os.getenv("LOG_LEVEL", _deep_get(config, "observability", "log_level", default="INFO"))
            ).upper()
        ),
        store_backend=str(
            os.getenv("DATAOBS_STORE_BACKEND", _deep_get(config, "store", "backend", default="memory"))
        ).lower(),
    )

    _validate(settings)
    logger.info(
        "DataObs settings loaded env=%s backend=%s tenant=%s es_host=%s",
        settings.runtime.env,
        settings.store_backend,
        settings.tenant_id,
        settings.elasticsearch.host_for_logs,
    )
    return settings


def _validate(settings: AppSettings) -> None:
    banned = {"changeme", "dataobs_poc_elastic", "dataobs_poc_kibana"}
    if settings.runtime.env == "production":
        if settings.auth.provider != "oidc" and not settings.auth.api_token:
            raise ConfigurationError("Legacy API_TOKEN is absent; production now requires DATAOBS_AUTH_PROVIDER=oidc.")
        if settings.auth.allow_unauthenticated_dev:
            raise ConfigurationError("Production forbids unauthenticated dev mode.")
        if settings.store_backend != "elasticsearch":
            raise ConfigurationError(
                "Production requires DATAOBS_STORE_BACKEND=elasticsearch and forbids memory as authoritative product state; optional exporters cannot hold authoritative product state."
            )
        if not settings.elasticsearch.url:
            raise ConfigurationError("Production requires ELASTICSEARCH_URL.")
        if not (settings.elasticsearch.api_key or (settings.elasticsearch.user and settings.elasticsearch.password)):
            raise ConfigurationError("Production requires Elasticsearch credentials or API key.")
        if settings.elasticsearch.password and settings.elasticsearch.password.lower() in banned:
            raise ConfigurationError("Production forbids default/changeme Elasticsearch passwords.")
        if settings.auth.provider != "oidc":
            raise ConfigurationError("Production requires DATAOBS_AUTH_PROVIDER=oidc; shared tokens are forbidden.")
        oidc = settings.auth.oidc
        if not oidc.issuer.startswith("https://") or not oidc.audience:
            raise ConfigurationError("Production OIDC requires an HTTPS issuer and explicit audience.")
        if not oidc.allowed_algorithms or any(
            not alg.startswith(("RS", "ES", "PS", "Ed")) for alg in oidc.allowed_algorithms
        ):
            raise ConfigurationError("Production OIDC algorithms must be an explicit asymmetric allowlist.")
        if not oidc.group_role_mappings and not oidc.platform_admin_groups:
            raise ConfigurationError("Production requires at least one trusted OIDC authorisation mapping.")
        if not settings.elasticsearch.verify_tls:
            raise ConfigurationError("Production requires TLS verification.")

    if settings.runtime.env in {"development", "poc", "test"} and not settings.elasticsearch.verify_tls:
        logger.warning("ELASTICSEARCH_VERIFY_TLS=false in %s mode.", settings.runtime.env)
