from __future__ import annotations

import hashlib
import json

from .models import PolicyDecision, RequirementState

POLICY_ID = "dataobs-incident-review"
POLICY_VERSION = "1.0.0"
POLICY_SEMANTICS = {"critical": "required", "high": "required", "default": "not_required"}
POLICY_HASH = hashlib.sha256(json.dumps(POLICY_SEMANTICS, sort_keys=True).encode()).hexdigest()


def decide(severity: str) -> PolicyDecision:
    required = severity in {"critical", "high"}
    return PolicyDecision(
        policy_id=POLICY_ID,
        policy_version=POLICY_VERSION,
        policy_hash=POLICY_HASH,
        decision=RequirementState.REQUIRED if required else RequirementState.NOT_REQUIRED,
        decision_reason=f"severity_{severity}_{'requires' if required else 'does_not_require'}_review",
    )
