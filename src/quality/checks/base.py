"""
DataObs — Base Quality Check

All quality checks inherit from BaseCheck.
Each check must implement `run()` and return a CheckResult.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class CheckResult:
    check_type: str
    dataset: str
    status: str  # PASS | FAIL | ERROR | WARN
    severity: str  # critical | high | medium | low
    message: str
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    metric_value: Optional[float] = None
    threshold: Optional[float] = None

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    def to_es_doc(self) -> dict:
        return {
            "@timestamp": self.checked_at.isoformat(),
            "check_type": self.check_type,
            "dataset": self.dataset,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "details": self.details,
        }


class BaseCheck(ABC):
    """
    Abstract base class for all DataObs quality checks.

    Subclasses must implement `run(config, connection)` and return CheckResult.
    """

    check_type: str = "base"

    @abstractmethod
    def run(self, config: dict, connection: Any) -> CheckResult: ...

    def _pass(self, dataset: str, message: str, severity: str = "low", **kwargs) -> CheckResult:
        return CheckResult(
            check_type=self.check_type,
            dataset=dataset,
            status="PASS",
            severity=severity,
            message=message,
            **kwargs,
        )

    def _fail(self, dataset: str, message: str, severity: str, **kwargs) -> CheckResult:
        return CheckResult(
            check_type=self.check_type,
            dataset=dataset,
            status="FAIL",
            severity=severity,
            message=message,
            **kwargs,
        )

    def _error(self, dataset: str, exc: Exception) -> CheckResult:
        return CheckResult(
            check_type=self.check_type,
            dataset=dataset,
            status="ERROR",
            severity="critical",
            message=f"Check execution failed: {exc}",
            details={"exception": str(exc)},
        )
