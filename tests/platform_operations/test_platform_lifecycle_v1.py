from dataclasses import replace

import pytest

from src.platform_lifecycle import LifecycleError, PlatformLifecycleService


def environment(service, key="env"):
    return service.create_environment(
        {"environment_id": "prod-env", "name": "Production", "region": "eu-west-1", "desired_state": {"release": "a"}},
        "alice",
        key,
    )


def test_environment_transition_occ_and_idempotent_create():
    service = PlatformLifecycleService()
    first = environment(service)
    assert environment(service) == first
    changed = service.transition(
        "environment", "prod-env", "provisioning", "alice", "environments:write", "approved", 1, "t1"
    )
    assert changed["revision"] == 2
    with pytest.raises(LifecycleError, match="cannot transition"):
        service.transition("environment", "prod-env", "ready", "alice", "environments:write", "skip", 2, "t2")
    with pytest.raises(LifecycleError) as error:
        service.transition("environment", "prod-env", "configured", "alice", "environments:write", "stale", 1, "t3")
    assert error.value.code == "revision_conflict"


def test_cluster_rejects_unsupported_and_duplicate():
    service = PlatformLifecycleService()
    payload = {"cluster_id": "cluster-one", "kubernetes_version": "1.30.4", "region": "eu-west-1"}
    service.register_cluster(payload, "alice", "one")
    with pytest.raises(LifecycleError) as duplicate:
        service.register_cluster(payload, "alice", "two")
    assert duplicate.value.code == "duplicate_resource"
    with pytest.raises(LifecycleError) as unsupported:
        service.register_cluster(
            {**payload, "cluster_id": "cluster-two", "kubernetes_version": "1.31.0"}, "alice", "three"
        )
    assert unsupported.value.code == "unsupported_kubernetes_version"


def test_installation_requires_exact_sha_and_safe_names():
    service = PlatformLifecycleService()
    environment(service)
    service.register_cluster({"cluster_id": "cluster-one", "kubernetes_version": "1.30.1"}, "alice", "c")
    payload = {
        "installation_id": "install-one",
        "cluster_id": "cluster-one",
        "environment_id": "prod-env",
        "namespace": "dataobs-prod",
        "helm_release_name": "dataobs-prod",
        "release_sha": "main",
    }
    with pytest.raises(LifecycleError) as error:
        service.register_installation(payload, "alice", "i")
    assert error.value.code == "mutable_release_rejected"
    assert service.register_installation({**payload, "release_sha": "a" * 40}, "alice", "i2")["state"] == "planned"


def test_tenant_onboarding_validation_and_activation_sequence():
    service = PlatformLifecycleService()
    environment(service)
    request = {
        "tenant_id": "tenant-one",
        "name": "Tenant",
        "requested_environment": "prod-env",
        "region_requirements": ["eu-west-1"],
        "initial_administrators": ["oidc:user:1"],
    }
    tenant = service.request_tenant(request, "alice", "r")
    for target, revision in [("approved", 1), ("provisioning", 2), ("validating", 3), ("active", 4)]:
        tenant = service.transition(
            "tenant", "tenant-one", target, "alice", "tenants:provision", target, revision, target
        )
    assert tenant["state"] == "active"


def test_tenant_rejects_missing_admin_region_and_physical_profile():
    service = PlatformLifecycleService()
    environment(service)
    base = {"tenant_id": "tenant-one", "requested_environment": "prod-env", "initial_administrators": ["user"]}
    for update, code in [
        ({"initial_administrators": []}, "initial_administrator_required"),
        ({"region_requirements": ["us-east-1"]}, "residency_constraint_unsatisfied"),
        ({"isolation_profile": "dedicated_installation"}, "unsupported_isolation_profile"),
    ]:
        with pytest.raises(LifecycleError) as error:
            service.request_tenant({**base, **update}, "alice", code)
        assert error.value.code == code


def test_offboarding_never_immediately_deletes_and_preview_is_redacted():
    service = PlatformLifecycleService()
    environment(service)
    service.request_tenant(
        {"tenant_id": "tenant-one", "requested_environment": "prod-env", "initial_administrators": ["user"]},
        "alice",
        "r",
    )
    tenant = service.repo.get("tenant", "tenant-one")
    service.repo.save("tenant", replace(tenant, state="suspended", revision=2), 1)
    offboarded = service.transition(
        "tenant", "tenant-one", "offboarding", "alice", "tenants:offboard", "requested", 2, "off"
    )
    assert offboarded["state"] == "offboarding"
    preview = service.offboarding_preview("tenant-one")
    assert preview["dry_run"] and not preview["contains_tenant_data"] and "backup_not_verified" in preview["blockers"]


def test_deletion_requires_backup_and_independent_approval():
    service = PlatformLifecycleService()
    environment(service)
    service.request_tenant(
        {"tenant_id": "tenant-one", "requested_environment": "prod-env", "initial_administrators": ["user"]},
        "alice",
        "r",
    )
    tenant = service.repo.get("tenant", "tenant-one")
    service.repo.save("tenant", replace(tenant, state="offboarding", revision=2), 1)
    with pytest.raises(LifecycleError) as error:
        service.transition("tenant", "tenant-one", "deleting", "alice", "tenants:offboard", "delete", 2, "d")
    assert error.value.code == "backup_not_verified"
    tenant = service.repo.get("tenant", "tenant-one")
    service.repo.save("tenant", replace(tenant, backup_verified=True, revision=3), 2)
    approved = service.approve_deletion("tenant-one", "bob", 3)
    result = service.transition(
        "tenant", "tenant-one", "deleting", "carol", "tenants:offboard", "approved", approved["revision"], "d2"
    )
    assert result["state"] == "deleting" and result["deletion_approved_by"] == "bob"


def test_fleet_unknown_is_not_healthy_and_skew_is_explicit():
    service = PlatformLifecycleService()
    assert service.fleet()["aggregate"]["healthy"] == 0
    assert service.fleet()["aggregate"]["release_skew"] == "none"


def test_approved_plan_is_immutable_and_failed_rollout_requires_rollback():
    from src.platform_lifecycle.planning import create_plan

    plan = create_plan("prod-env", {"release_sha": "a" * 40}, {"release_sha": "b" * 40})
    plan = plan.advance("validated").advance("approval_required").advance("approved")
    with pytest.raises(LifecycleError):
        plan.advance("validated")
    plan = plan.advance("executing").advance("failed").advance("rollback_required").advance("rolled_back")
    assert plan.state == "rolled_back"


def test_promotion_fails_closed_for_unknown_evidence_and_unapproved_release():
    from src.platform_lifecycle.planning import validate_promotion

    evidence = {
        "release_sha": "a" * 40,
        "signature_valid": True,
        "digests_match": True,
        "source_certified": True,
        "destination_supported": True,
        "migration_compatible": True,
        "backup_ready": True,
        "security_certified": True,
        "slo_healthy": None,
        "release_decision": "NO_GO",
    }
    with pytest.raises(LifecycleError) as unknown:
        validate_promotion(evidence)
    assert unknown.value.code == "mandatory_evidence_unknown"
    evidence["slo_healthy"] = True
    with pytest.raises(LifecycleError) as decision:
        validate_promotion(evidence)
    assert decision.value.code == "release_not_approved"
