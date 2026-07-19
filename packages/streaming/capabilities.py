from enum import Enum

from pydantic import BaseModel


class CapabilityState(str, Enum):
    NOT_IMPLEMENTED = "not_implemented"
    NOT_CONFIGURED = "not_configured"
    PARTIAL = "partial"
    AVAILABLE = "available"


class AdapterCapabilities(BaseModel):
    provider: str
    state: CapabilityState
    inventory: CapabilityState
    offsets: CapabilityState
    groups: CapabilityState
