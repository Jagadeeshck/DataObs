from .base import ProductEntity


class Monitor(ProductEntity):
    monitor_type: str
    asset_id: str
    condition: str
    severity: str = "medium"
    threshold_ref: str | None = None
    baseline_ref: str | None = None
    schedule: str | None = None
    owner: str | None = None
    notification_policy: str | None = None
    enabled: bool = True
