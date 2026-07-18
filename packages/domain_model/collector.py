from datetime import datetime
from typing import List

from .base import ProductEntity


class Collector(ProductEntity):
    collector_type: str
    version: str
    deployment_mode: str = "standalone"
    health: str = "unknown"
    capabilities: List[str] = []
    last_heartbeat: datetime | None = None
    location: str | None = None
    policy_revision: str | None = None
