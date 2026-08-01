from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    field: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...] = ()


@dataclass(frozen=True)
class ConnectionTestResult:
    connected: bool
    latency_ms: int | None = None
    error_code: str | None = None
    message: str | None = None
