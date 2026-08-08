from __future__ import annotations

from .models import LifecycleState


class InvalidTransition(ValueError):
    pass


class ReasonRequired(ValueError):
    pass


TRANSITIONS = {
    LifecycleState.DRAFT: {LifecycleState.IN_REVIEW},
    LifecycleState.IN_REVIEW: {LifecycleState.APPROVED, LifecycleState.REJECTED},
    LifecycleState.APPROVED: {LifecycleState.ACTIVE},
    LifecycleState.ACTIVE: {LifecycleState.DEPRECATED},
    LifecycleState.DEPRECATED: {LifecycleState.RETIRED},
}
REASON_REQUIRED = {LifecycleState.REJECTED, LifecycleState.DEPRECATED, LifecycleState.RETIRED}


def validate_transition(current: LifecycleState, target: LifecycleState, reason: str = "") -> None:
    if target not in TRANSITIONS.get(current, set()):
        raise InvalidTransition(f"cannot transition {current.value} to {target.value}")
    if target in REASON_REQUIRED and not reason.strip():
        raise ReasonRequired(f"reason is required for {target.value}")
