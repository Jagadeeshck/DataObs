"""Metadata-only credential inventory and rotation state machine."""

from __future__ import annotations

import hmac
import json
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from hashlib import sha256


class CredentialPolicyError(ValueError):
    pass


class RotationState(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    STAGED = "staged"
    VERIFICATION_PENDING = "verification_pending"
    VERIFIED = "verified"
    PROMOTED = "promoted"
    RETIRED = "retired"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class CredentialMetadata:
    credential_id: str
    credential_class: str
    owner: str
    provider_type: str
    reference_hash: str
    active_version: str
    evidence_available: bool = False
    status: str = "unknown"

    def __post_init__(self) -> None:
        if self.status == "healthy" and not self.evidence_available:
            raise CredentialPolicyError("missing evidence cannot be healthy")
        forbidden = ("password", "secret_value", "private_key", "authorization")
        document = json.dumps(self.__dict__).lower()
        if any(name in document for name in forbidden):
            raise CredentialPolicyError("credential inventory must contain references only")


@dataclass(frozen=True)
class RotationPlan:
    rotation_id: str
    credential_id: str
    current_version: str
    proposed_reference_hash: str
    requester: str
    expires_at: datetime
    high_risk: bool
    approvals: tuple[str, ...] = ()
    state: RotationState = RotationState.PROPOSED
    revision: int = 1

    @property
    def etag(self) -> str:
        return '"' + sha256(f"{self.rotation_id}:{self.revision}".encode()).hexdigest() + '"'

    def approve(self, actor: str, now: datetime) -> "RotationPlan":
        if now >= self.expires_at or self.state not in {RotationState.PROPOSED, RotationState.APPROVED}:
            raise CredentialPolicyError("rotation is not approvable")
        if actor == self.requester or actor in self.approvals:
            raise CredentialPolicyError("separation of duties violation")
        approvals = (*self.approvals, actor)
        state = RotationState.APPROVED if len(approvals) >= (2 if self.high_risk else 1) else self.state
        return replace(self, approvals=approvals, state=state, revision=self.revision + 1)

    def transition(
        self, target: RotationState, now: datetime, *, verification_succeeded: bool = True
    ) -> "RotationPlan":
        if now >= self.expires_at:
            raise CredentialPolicyError("rotation plan expired")
        allowed = {
            RotationState.APPROVED: {RotationState.STAGED},
            RotationState.STAGED: {RotationState.VERIFICATION_PENDING},
            RotationState.VERIFICATION_PENDING: {RotationState.VERIFIED, RotationState.FAILED},
            RotationState.VERIFIED: {RotationState.PROMOTED},
            RotationState.PROMOTED: {RotationState.RETIRED, RotationState.ROLLED_BACK},
            RotationState.RETIRED: {RotationState.COMPLETED},
        }
        if target not in allowed.get(self.state, set()):
            raise CredentialPolicyError("invalid rotation transition")
        if target == RotationState.VERIFIED and not verification_succeeded:
            raise CredentialPolicyError("verification failed")
        return replace(self, state=target, revision=self.revision + 1)


@dataclass(frozen=True)
class VerificationKey:
    key_id: str
    key: bytes
    accept_until: datetime


class HMACKeyring:
    """Versioned signer; key bytes never appear in encoded tokens."""

    def __init__(self, active: VerificationKey, previous: tuple[VerificationKey, ...] = ()):
        if any(item.key_id == active.key_id for item in previous):
            raise CredentialPolicyError("key IDs must be unique")
        self._active, self._keys = active, {item.key_id: item for item in (active, *previous)}

    def sign(self, payload: bytes) -> str:
        signature = hmac.new(self._active.key, payload, sha256).hexdigest()
        return f"{self._active.key_id}.{signature}"

    def verify(self, payload: bytes, token: str, now: datetime) -> bool:
        try:
            key_id, signature = token.split(".", 1)
            key = self._keys[key_id]
        except (ValueError, KeyError):
            return False
        return now <= key.accept_until and hmac.compare_digest(
            hmac.new(key.key, payload, sha256).hexdigest(), signature
        )
