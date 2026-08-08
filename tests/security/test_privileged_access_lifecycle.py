from datetime import datetime, timedelta, timezone

import pytest

from src.security.credential_lifecycle import (
    CredentialMetadata,
    CredentialPolicyError,
    HMACKeyring,
    RotationPlan,
    RotationState,
    VerificationKey,
)
from src.security.permissions import Permission
from src.security.privileged_access import BreakGlassGrant, BreakGlassState, PrivilegedAccessError, StrongAuthEvidence

NOW = datetime(2026, 8, 8, tzinfo=timezone.utc)


def grant(risk="high"):
    return BreakGlassGrant.request(
        requester="alice",
        tenant_id="t1",
        environment="prod",
        permissions={Permission.CREDENTIALS_ROTATE},
        justification="Restore credential availability",
        change_reference="INC-123",
        starts_at=NOW,
        duration=timedelta(minutes=30),
        risk=risk,
    )


def test_break_glass_separation_strong_auth_scope_and_expiry():
    with pytest.raises(PrivilegedAccessError, match="own"):
        grant().approve("alice", NOW)
    approved = grant().approve("bob", NOW)
    with pytest.raises(PrivilegedAccessError, match="strong"):
        approved.activate("alice", StrongAuthEvidence(NOW, "aal2", frozenset(), False), NOW)
    active = approved.activate("alice", StrongAuthEvidence(NOW, "aal2", frozenset({"mfa"}), True), NOW)
    assert active.authorizes(
        principal="alice", tenant_id="t1", environment="prod", permission=Permission.CREDENTIALS_ROTATE, now=NOW
    )
    assert not active.authorizes(
        principal="alice", tenant_id="t2", environment="prod", permission=Permission.CREDENTIALS_ROTATE, now=NOW
    )
    assert not active.authorizes(
        principal="alice",
        tenant_id="t1",
        environment="prod",
        permission=Permission.CREDENTIALS_ROTATE,
        now=NOW + timedelta(hours=1),
    )
    assert active.revoke().state == BreakGlassState.REVOKED


def test_critical_grant_needs_two_distinct_approvers():
    first = grant("critical").approve("bob", NOW)
    assert first.state == BreakGlassState.REQUESTED
    with pytest.raises(PrivilegedAccessError, match="duplicate"):
        first.approve("bob", NOW)
    assert first.approve("carol", NOW).state == BreakGlassState.APPROVED


def test_rotation_requires_approval_verification_and_supports_rollback():
    plan = RotationPlan("r1", "cursor", "v1", "sha256:new", "alice", NOW + timedelta(hours=1), False)
    with pytest.raises(CredentialPolicyError, match="duties"):
        plan.approve("alice", NOW)
    plan = plan.approve("bob", NOW).transition(RotationState.STAGED, NOW)
    with pytest.raises(CredentialPolicyError, match="invalid"):
        plan.transition(RotationState.PROMOTED, NOW)
    plan = plan.transition(RotationState.VERIFICATION_PENDING, NOW).transition(RotationState.VERIFIED, NOW)
    plan = plan.transition(RotationState.PROMOTED, NOW)
    assert plan.transition(RotationState.ROLLED_BACK, NOW).state == RotationState.ROLLED_BACK


def test_inventory_missing_evidence_is_not_healthy_and_rejects_secret_fields():
    with pytest.raises(CredentialPolicyError, match="evidence"):
        CredentialMetadata("c", "cursor_signing", "team0", "kubernetes", "sha256:x", "v1", status="healthy")
    with pytest.raises(CredentialPolicyError, match="references"):
        CredentialMetadata("c", "password", "team0", "kubernetes", "sha256:x", "v1")


def test_hmac_key_overlap_is_bounded_and_unknown_ids_fail_closed():
    old = VerificationKey("old", b"synthetic-old", NOW + timedelta(minutes=5))
    ring_old = HMACKeyring(old)
    token = ring_old.sign(b"cursor")
    ring = HMACKeyring(VerificationKey("new", b"synthetic-new", NOW + timedelta(hours=1)), (old,))
    assert ring.verify(b"cursor", token, NOW)
    assert not ring.verify(b"cursor", token, NOW + timedelta(minutes=6))
    assert not ring.verify(b"cursor", "unknown.00", NOW)
