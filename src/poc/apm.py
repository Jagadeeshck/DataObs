"""
src/poc/apm.py
──────────────
Elastic APM telemetry for the DataObs POC pipeline.

This is the default telemetry path. Traces (transactions/spans) and
custom metrics are shipped directly to the Elastic APM Server hosted
by the Fleet-managed `elastic-agent` container at
``http://elastic-agent:8200``. No standalone OpenTelemetry Collector
is required.

Design goals
------------
1. Module import must NEVER fail — if ``elastic-apm`` is not installed
   or the endpoint is unreachable, telemetry degrades to structured
   log lines and the pipeline keeps running.
2. No retry-spam: when APM is disabled, instrumentation is a pure
   no-op. When the endpoint is briefly unavailable, the agent drops
   events silently rather than flooding the log.
3. Stage / Spark span helpers mirror the previous OTel API
   (``stage()``, ``span()``) so existing call sites don't need to
   change shape.

Environment variables (read at bootstrap):
  ELASTIC_APM_SERVER_URL    APM Server URL (default: http://elastic-agent:8200)
  ELASTIC_APM_SECRET_TOKEN  Shared secret (default: dataobs_poc_apm_token)
  ELASTIC_APM_SERVICE_NAME  Service name for the run (default: dataobs-poc-pipeline)
  ELASTIC_APM_ENVIRONMENT   Environment label (default: poc)
  ELASTIC_APM_DISABLED      "true" → fully suppress agent (no-op mode)
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

logger = logging.getLogger(__name__)

try:
    import elasticapm
    from elasticapm import Client as _ApmClient
    _APM_AVAILABLE = True
except Exception:  # noqa: BLE001
    elasticapm = None  # type: ignore[assignment]
    _ApmClient = None  # type: ignore[assignment]
    _APM_AVAILABLE = False


_DEFAULT_SERVER_URL = "http://elastic-agent:8200"
_DEFAULT_TOKEN = "dataobs_poc_apm_token"
_DEFAULT_SERVICE = "dataobs-poc-pipeline"
_DEFAULT_ENV = "poc"


def _apm_disabled() -> bool:
    return os.environ.get("ELASTIC_APM_DISABLED", "false").lower() == "true"


class ApmTelemetry:
    """
    Thin wrapper around the Elastic APM Python client.

    Use as a context manager around an entire run; ``stage()`` and
    ``span()`` create child spans. When ``elastic-apm`` is not
    installed or ``ELASTIC_APM_DISABLED=true`` the wrapper degrades
    to no-op logging — the pipeline never raises a telemetry error.
    """

    def __init__(
        self,
        service_name: Optional[str] = None,
        environment: Optional[str] = None,
        server_url: Optional[str] = None,
        secret_token: Optional[str] = None,
        global_labels: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.service_name = service_name or os.environ.get(
            "ELASTIC_APM_SERVICE_NAME", _DEFAULT_SERVICE
        )
        self.environment = environment or os.environ.get(
            "ELASTIC_APM_ENVIRONMENT", _DEFAULT_ENV
        )
        self.server_url = server_url or os.environ.get(
            "ELASTIC_APM_SERVER_URL", _DEFAULT_SERVER_URL
        )
        self.secret_token = secret_token or os.environ.get(
            "ELASTIC_APM_SECRET_TOKEN", _DEFAULT_TOKEN
        )
        self.global_labels = global_labels or {
            "service.namespace": "dataobs",
            "deployment.environment.name": self.environment,
        }
        self._client: Optional[Any] = None
        self._enabled = False

    def start(self) -> None:
        if _apm_disabled():
            logger.info("[apm] ELASTIC_APM_DISABLED=true — running in no-op mode.")
            return
        if not _APM_AVAILABLE:
            logger.info(
                "[apm] elastic-apm package not installed — running in no-op mode "
                "(install elastic-apm>=6.20 to enable APM)."
            )
            return
        try:
            # transport_class set to the default HTTP transport;
            # disable_metrics='*' is *not* used — we want runtime metrics.
            self._client = _ApmClient(
                {
                    "SERVICE_NAME": self.service_name,
                    "ENVIRONMENT": self.environment,
                    "SERVER_URL": self.server_url,
                    "SECRET_TOKEN": self.secret_token,
                    "GLOBAL_LABELS": ",".join(
                        f"{k}={v}" for k, v in self.global_labels.items()
                    ),
                    # Avoid noisy retry loops if the server is briefly
                    # unavailable (the agent drops events silently).
                    "TRANSPORT_CLASS": "elasticapm.transport.http.Transport",
                    "API_REQUEST_TIME": "10s",
                    "RECORDING": True,
                    "INSTRUMENT": True,
                    "CENTRAL_CONFIG": False,
                    "VERIFY_SERVER_CERT": False,
                }
            )
            elasticapm.instrument()  # auto-instrument supported libs
            self._enabled = True
            logger.info(
                "[apm] Elastic APM agent started → service=%s env=%s url=%s",
                self.service_name,
                self.environment,
                self.server_url,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[apm] Failed to start Elastic APM agent: %s", exc)
            self._client = None
            self._enabled = False

    def shutdown(self) -> None:
        if self._client is None:
            return
        try:
            self._client.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug("[apm] client.close() raised (ignored): %s", exc)
        finally:
            self._client = None
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def client(self) -> Optional[Any]:
        return self._client

    # ── Span helpers ────────────────────────────────────────────────────────
    @contextmanager
    def transaction(
        self,
        name: str,
        transaction_type: str = "pipeline",
        labels: Optional[Dict[str, Any]] = None,
    ) -> Iterator[None]:
        """Wrap a top-level pipeline run in an APM transaction."""
        if not self._enabled or self._client is None:
            logger.info("[apm][txn=%s] start (no-op)", name)
            try:
                yield
            finally:
                logger.info("[apm][txn=%s] end (no-op)", name)
            return

        self._client.begin_transaction(transaction_type)
        try:
            if labels:
                elasticapm.label(**labels)
            yield
            elasticapm.set_transaction_outcome(outcome="success")
            self._client.end_transaction(name, "success")
        except Exception as exc:
            try:
                self._client.capture_exception()
            except Exception:  # noqa: BLE001
                pass
            elasticapm.set_transaction_outcome(outcome="failure")
            self._client.end_transaction(name, "failure")
            raise

    @contextmanager
    def stage(
        self,
        stage_name: str,
        span_type: str = "pipeline.stage",
        labels: Optional[Dict[str, Any]] = None,
    ) -> Iterator[None]:
        """Wrap a single pipeline stage in an APM span."""
        if not self._enabled:
            logger.info("[apm][stage=%s] start (no-op)", stage_name)
            try:
                yield
            finally:
                logger.info("[apm][stage=%s] end (no-op)", stage_name)
            return

        with elasticapm.capture_span(name=stage_name, span_type=span_type) as span:
            if labels:
                try:
                    elasticapm.label(**{f"stage.{k}": v for k, v in labels.items()})
                except Exception:  # noqa: BLE001
                    pass
            yield span

    @contextmanager
    def span(
        self,
        name: str,
        span_type: str = "custom",
        labels: Optional[Dict[str, Any]] = None,
    ) -> Iterator[None]:
        """General-purpose APM span (for nested Spark stages)."""
        if not self._enabled:
            try:
                yield
            finally:
                return
        with elasticapm.capture_span(name=name, span_type=span_type):
            if labels:
                try:
                    elasticapm.label(**labels)
                except Exception:  # noqa: BLE001
                    pass
            yield

    # ── Custom metric / label helpers ───────────────────────────────────────
    def label(self, **kwargs: Any) -> None:
        if not self._enabled:
            return
        try:
            elasticapm.label(**kwargs)
        except Exception:  # noqa: BLE001
            pass

    def capture_exception(self) -> None:
        if self._enabled and self._client is not None:
            try:
                self._client.capture_exception()
            except Exception:  # noqa: BLE001
                pass


def build_default_apm() -> ApmTelemetry:
    """Convenience factory that reads env vars only."""
    return ApmTelemetry()
