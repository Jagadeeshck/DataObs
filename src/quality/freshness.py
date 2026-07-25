"""
DataObs — Data Freshness Monitor

Detects stale data by tracking the last update time of datasets.
Emits OpenTelemetry metrics and sends alerts when SLA thresholds are breached.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import boto3
import sqlalchemy
from elasticsearch import Elasticsearch
from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# ── OpenTelemetry instrumentation ──────────────────────────────────────────────
tracer = trace.get_tracer("dataobs.freshness")
meter = metrics.get_meter("dataobs.freshness")

freshness_gauge = meter.create_gauge(
    name="dataobs.dataset.freshness_age_seconds",
    description="Age of the most recent data in the dataset (seconds)",
    unit="s",
)
freshness_breach_counter = meter.create_counter(
    name="dataobs.dataset.freshness_breach_total",
    description="Number of freshness SLA breaches",
)

# ── SQL identifier validation ──────────────────────────────────────────────────
# Allows only alphanumeric, underscore, and dot (for schema.table notation).
# This prevents SQL injection via config-supplied table/column names.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def _validate_sql_identifier(value: str, label: str) -> str:
    """Raise ValueError if *value* is not a safe SQL identifier."""
    if not _IDENTIFIER_RE.match(value):
        raise ValueError(
            f"Invalid SQL identifier for {label!r}: {value!r}. "
            "Only letters, digits, underscores, and dots are allowed."
        )
    return value


@dataclass
class FreshnessConfig:
    dataset_name: str
    source_type: str  # rds | s3 | glue | athena
    max_age_minutes: int
    severity: str = "high"  # critical | high | medium | low
    partition_column: Optional[str] = None
    timestamp_column: Optional[str] = None
    connection_string: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_prefix: Optional[str] = None
    glue_database: Optional[str] = None
    glue_table: Optional[str] = None


@dataclass
class FreshnessResult:
    dataset_name: str
    checked_at: datetime
    last_updated_at: Optional[datetime]
    age_seconds: Optional[float]
    is_stale: bool
    severity: str
    max_age_seconds: float
    details: dict = field(default_factory=dict)

    @property
    def age_minutes(self) -> Optional[float]:
        return self.age_seconds / 60 if self.age_seconds is not None else None

    def to_es_doc(self) -> dict:
        return {
            "@timestamp": self.checked_at.isoformat(),
            "dataset": self.dataset_name,
            "check_type": "freshness",
            "last_updated_at": self.last_updated_at.isoformat() if self.last_updated_at else None,
            "age_seconds": self.age_seconds,
            "age_minutes": self.age_minutes,
            "is_stale": self.is_stale,
            "severity": self.severity,
            "max_age_seconds": self.max_age_seconds,
            "status": "FAIL" if self.is_stale else "PASS",
            "details": self.details,
        }


class FreshnessMonitor:
    """
    Checks data freshness across multiple source types.
    Results are indexed into Elasticsearch and emitted as OTEL metrics.
    """

    def __init__(self, es_client: Elasticsearch, aws_region: str = "eu-west-1"):
        self.es = es_client
        self.aws_region = aws_region
        self._glue_client = None
        self._s3_client = None

    @property
    def glue_client(self):
        if self._glue_client is None:
            self._glue_client = boto3.client("glue", region_name=self.aws_region)
        return self._glue_client

    @property
    def s3_client(self):
        if self._s3_client is None:
            self._s3_client = boto3.client("s3", region_name=self.aws_region)
        return self._s3_client

    @tracer.start_as_current_span("check_freshness")
    def check(self, config: FreshnessConfig) -> FreshnessResult:
        """Run a freshness check for a single dataset configuration."""
        span = trace.get_current_span()
        span.set_attribute("dataobs.dataset", config.dataset_name)
        span.set_attribute("dataobs.source_type", config.source_type)

        now = datetime.now(timezone.utc)
        max_age_seconds = config.max_age_minutes * 60

        try:
            last_updated = self._get_last_updated(config)
            if last_updated is None:
                logger.warning("Could not determine last update time for %s", config.dataset_name)
                result = FreshnessResult(
                    dataset_name=config.dataset_name,
                    checked_at=now,
                    last_updated_at=None,
                    age_seconds=None,
                    is_stale=True,
                    severity=config.severity,
                    max_age_seconds=max_age_seconds,
                    details={"error": "Could not determine last update time"},
                )
            else:
                age_seconds = (now - last_updated).total_seconds()
                is_stale = age_seconds > max_age_seconds

                result = FreshnessResult(
                    dataset_name=config.dataset_name,
                    checked_at=now,
                    last_updated_at=last_updated,
                    age_seconds=age_seconds,
                    is_stale=is_stale,
                    severity=config.severity,
                    max_age_seconds=max_age_seconds,
                    details={"source_type": config.source_type},
                )

                attrs = {
                    "dataobs.dataset": config.dataset_name,
                    "dataobs.source_type": config.source_type,
                    "dataobs.severity": config.severity,
                }
                freshness_gauge.set(age_seconds, attrs)
                if is_stale:
                    freshness_breach_counter.add(1, attrs)
                    span.set_status(
                        Status(StatusCode.ERROR, f"Freshness SLA breached: {age_seconds:.0f}s > {max_age_seconds:.0f}s")
                    )
                    logger.error(
                        "FRESHNESS BREACH: %s | age=%.1fm | max=%.1fm | severity=%s",
                        config.dataset_name,
                        age_seconds / 60,
                        config.max_age_minutes,
                        config.severity,
                    )
                else:
                    logger.info("Freshness OK: %s | age=%.1fm", config.dataset_name, age_seconds / 60)

        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            logger.exception("Freshness check failed for %s", config.dataset_name)
            result = FreshnessResult(
                dataset_name=config.dataset_name,
                checked_at=now,
                last_updated_at=None,
                age_seconds=None,
                is_stale=True,
                severity="critical",
                max_age_seconds=max_age_seconds,
                details={"error": str(exc)},
            )

        self._index_result(result)
        return result

    def _get_last_updated(self, config: FreshnessConfig) -> Optional[datetime]:
        """Dispatch to the correct source connector."""
        if config.source_type == "glue":
            return self._check_glue(config)
        elif config.source_type == "s3":
            return self._check_s3(config)
        elif config.source_type in ("rds", "postgresql", "mysql"):
            return self._check_rds(config)
        elif config.source_type == "athena":
            return self._check_athena(config)
        else:
            raise ValueError(f"Unsupported source_type: {config.source_type}")

    def _check_glue(self, config: FreshnessConfig) -> Optional[datetime]:
        """Get the last time a Glue table partition was updated."""
        try:
            response = self.glue_client.get_table(
                DatabaseName=config.glue_database,
                Name=config.glue_table,
            )
            table = response["Table"]
            updated = table.get("UpdateTime") or table.get("CreateTime")
            if updated and updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            return updated
        except Exception as e:
            logger.error("Glue freshness check error: %s", e)
            return None

    def _check_s3(self, config: FreshnessConfig) -> Optional[datetime]:
        """Get the last modified time of the newest object in an S3 prefix."""
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            latest = None
            for page in paginator.paginate(Bucket=config.s3_bucket, Prefix=config.s3_prefix or ""):
                for obj in page.get("Contents", []):
                    lm = obj["LastModified"]
                    if lm.tzinfo is None:
                        lm = lm.replace(tzinfo=timezone.utc)
                    if latest is None or lm > latest:
                        latest = lm
            return latest
        except Exception as e:
            logger.error("S3 freshness check error: %s", e)
            return None

    def _check_rds(self, config: FreshnessConfig) -> Optional[datetime]:
        """Query max(timestamp_column) from a relational database table.

        Both the table name and timestamp column name are validated against a
        strict identifier regex before interpolation to prevent SQL injection.
        """
        try:
            # --- Security: validate identifiers before string interpolation ---
            raw_table = config.dataset_name.split(".")[-1]
            table_name = _validate_sql_identifier(raw_table, "table_name")
            ts_col = _validate_sql_identifier(config.timestamp_column or "updated_at", "timestamp_column")
            # -------------------------------------------------------------------

            engine = sqlalchemy.create_engine(config.connection_string)
            with engine.connect() as conn:
                result = conn.execute(sqlalchemy.text(f"SELECT MAX({ts_col}) FROM {table_name}"))
                row = result.fetchone()
                if row and row[0]:
                    dt = row[0]
                    if hasattr(dt, "tzinfo") and dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
        except ValueError:
            raise
        except Exception as e:
            logger.error("RDS freshness check error: %s", e)
        return None

    def _check_athena(self, config: FreshnessConfig) -> Optional[datetime]:
        """Use Glue catalog metadata for Athena table freshness (same catalog).

        TODO: Replace with Athena-native query for partition-level freshness
        accuracy when partition metadata differs from Glue table UpdateTime.
        """
        return self._check_glue(config)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    def _index_result(self, result: FreshnessResult) -> None:
        """Write the freshness check result to Elasticsearch.

        Retries up to 3 times with exponential back-off on transient failures
        so that a brief Elasticsearch hiccup does not silently drop results.
        """
        self.es.index(
            index="dataobs-freshness",
            document=result.to_es_doc(),
        )
