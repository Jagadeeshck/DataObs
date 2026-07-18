from typing import List

from .base import ProductEntity


class Integration(ProductEntity):
    integration_kind: str
    version: str
    collection_mechanism: str
    capability_set: List[str] = []
    desired_state: str = "enabled"
    observed_state: str = "unknown"
    compatibility_status: str = "unknown"
