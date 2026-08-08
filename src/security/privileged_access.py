"""Fail-closed privileged-access domain rules.

This module is storage-neutral: production adapters must persist each projection
with OCC and append every decision to the security event stream.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from hashlib import sha256

from .permissions import Permission


class PrivilegedAccessError(ValueError):
    """A bounded, safe policy failure."""


class BreakGlassState(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    REVIEW_REQUIRED = "review_required"
    CLOSED = "closed"


ELIGIBLE_PERMISSIONS = frozenset(
    {Permission.IAM_WRITE, Permission.SERVICE_PRINCIPALS_WRITE, Permission.CREDENTIALS_ROTATE}
)


@dataclass(frozen=True)
class StrongAuthEvidence:
    authenticated_at: datetime
    acr: str
    amr: frozenset[str]
    mfa_present: bool

    def valid(self, now: datetime, *, accepted_acr: frozenset[str], max_age: timedelta) -> bool:
        age = now - self.authenticated_at
        return self.mfa_present and self.acr in accepted_acr and timedelta(0) <= age <= max_age


@dataclass(frozen=True)
class BreakGlassGrant:
    grant_id: str
    requester: str
    tenant_id: str
    environment: str
    permissions: frozenset[Permission]
    justification: str
    change_reference: str
    starts_at: datetime
    expires_at: datetime
    risk: str
    approvals: tuple[str, ...] = ()
    state: BreakGlassState = BreakGlassState.REQUESTED
    revision: int = 1
    policy_version: str = "privileged-access-v1"

    @classmethod
    def request(
        cls,
        *,
        requester: str,
        tenant_id: str,
        environment: str,
        permissions: set[Permission],
        justification: str,
        change_reference: str,
        starts_at: datetime,
        duration: timedelta,
        risk: str = "high",
    ) -> "BreakGlassGrant":
        if not tenant_id or not environment or "*" in {tenant_id, environment}:
            raise PrivilegedAccessError("bounded tenant and environment are required")
        if justification.strip().lower() in {"", "n/a", "test", "todo"} or len(justification) > 1000:
            raise PrivilegedAccessError("meaningful bounded justification is required")
        if not change_reference.strip() or len(change_reference) > 128:
            raise PrivilegedAccessError("change reference is required")
        if duration <= timedelta(0) or duration > timedelta(hours=4):
            raise PrivilegedAccessError("duration must be between zero and four hours")
        if not permissions or not permissions <= ELIGIBLE_PERMISSIONS:
            raise PrivilegedAccessError("permission is not break-glass eligible")
        digest = sha256(
            f"{requester}\0{tenant_id}\0{environment}\0{starts_at.isoformat()}\0{change_reference}".encode()
        ).hexdigest()[:32]
        return cls(
            digest,
            requester,
            tenant_id,
            environment,
            frozenset(permissions),
            justification,
            change_reference,
            starts_at,
            starts_at + duration,
            risk,
        )

    @property
    def etag(self) -> str:
        return '"' + sha256(f"{self.grant_id}:{self.revision}".encode()).hexdigest() + '"'

    def approve(self, approver: str, now: datetime) -> "BreakGlassGrant":
        if self.state not in {BreakGlassState.REQUESTED, BreakGlassState.APPROVED} or now >= self.expires_at:
            raise PrivilegedAccessError("grant is not approvable")
        if approver == self.requester:
            raise PrivilegedAccessError("requester cannot approve their own grant")
        if approver in self.approvals:
            raise PrivilegedAccessError("duplicate approver")
        approvals = (*self.approvals, approver)
        threshold = 2 if self.risk == "critical" else 1
        state = BreakGlassState.APPROVED if len(approvals) >= threshold else BreakGlassState.REQUESTED
        return replace(self, approvals=approvals, state=state, revision=self.revision + 1)

    def activate(self, actor: str, evidence: StrongAuthEvidence, now: datetime) -> "BreakGlassGrant":
        if (
            actor != self.requester
            or self.state != BreakGlassState.APPROVED
            or not (self.starts_at <= now < self.expires_at)
        ):
            raise PrivilegedAccessError("grant is not activatable")
        if not evidence.valid(
            now, accepted_acr=frozenset({"urn:dataobs:loa:2", "aal2"}), max_age=timedelta(minutes=10)
        ):
            raise PrivilegedAccessError("recent strong authentication is required")
        return replace(self, state=BreakGlassState.ACTIVE, revision=self.revision + 1)

    def authorizes(
        self, *, principal: str, tenant_id: str, environment: str, permission: Permission, now: datetime
    ) -> bool:
        return bool(
            self.state == BreakGlassState.ACTIVE
            and now < self.expires_at
            and principal == self.requester
            and tenant_id == self.tenant_id
            and environment == self.environment
            and permission in self.permissions
        )

    def revoke(self) -> "BreakGlassGrant":
        if self.state in {BreakGlassState.REJECTED, BreakGlassState.REVOKED, BreakGlassState.CLOSED}:
            raise PrivilegedAccessError("terminal grant is immutable")
        return replace(self, state=BreakGlassState.REVOKED, revision=self.revision + 1)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
