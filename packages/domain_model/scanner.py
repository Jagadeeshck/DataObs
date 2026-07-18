from datetime import datetime
from typing import Any, Dict, List

from .base import ProductEntity


class Scanner(ProductEntity):
    scanner_identity: str
    version: str
    supported_connectors: List[str] = []
    health: str = "unknown"
    last_heartbeat: datetime | None = None
    assigned_tasks: List[str] = []
    capacity: Dict[str, Any] = {}
    deployment_mode: str = "standalone"


class ScanPolicy(ProductEntity):
    source_id: str
    connector: str
    operation: str
    schedule: str | None = None
    timeout_seconds: int = 300
    concurrency: int = 1
    allowlist: List[str] = []
    denylist: List[str] = []
    safety_limits: Dict[str, Any] = {}
    credential_ref: str | None = None
    enabled: bool = True
