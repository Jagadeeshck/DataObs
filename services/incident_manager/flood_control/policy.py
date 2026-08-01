from dataclasses import dataclass


@dataclass(frozen=True)
class FloodPolicy:
    version: str = "v1"
    observation_seconds: int = 300
    elevated_count: int = 10
    flooding_count: int = 25
    event_rate_per_minute: float = 10.0
    unique_asset_threshold: int = 10
    unique_source_threshold: int = 5
    quiet_period_seconds: int = 600
    hysteresis_count: int = 5
    maximum_events: int = 1000


V1_FLOOD_POLICY = FloodPolicy()
