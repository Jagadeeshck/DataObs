from services.collection_manager import CollectionManagerService


def test_synthetic_scanner_flow_idempotency_and_tenant_isolation():
    svc = CollectionManagerService()
    svc.create_tenant({"tenant_id": "t1", "display_name": "Tenant 1", "namespace": "t1"})
    source = svc.create_source(
        "t1",
        {
            "source_name": "pg",
            "source_type": "postgres",
            "connector_type": "postgres",
            "endpoint": {"host": "db"},
            "credential_ref": "vault://pg",
        },
    )
    assert "password" not in source
    scanner = svc.register("scanners", "t1", {"scanner_identity": "scanner-a", "version": "0.1"}, "scanner")
    svc.heartbeat("scanners", "t1", scanner["id"], {"health": "healthy"})
    svc.create_policy(
        "t1", {"source_id": source["id"], "connector": "postgres", "operation": "schema_snapshot", "enabled": True}
    )
    task = svc.tasks_for_scanner("t1", scanner["id"])[0]
    svc.ack_task("t1", scanner["id"], task["id"])
    payload = {
        "source_id": source["id"],
        "fully_qualified_name": "db.public.orders",
        "namespace": "db",
        "asset_type": "table",
        "owner_team": "data-eng",
        "business_service": "orders",
        "schema": {"columns": [{"name": "id", "type": "int"}]},
    }
    r1 = svc.submit_result("t1", scanner["id"], task["id"], payload, "idem-1")
    r2 = svc.submit_result("t1", scanner["id"], task["id"], payload, "idem-1")
    assert r1 == r2
    assert r1["asset"]["pillar"] == "data"
    assert svc.repo.events[-1]["event_type"] == "schema_snapshot"
    assert svc.repo.list("assets", "t1")[0]["owner_team"] == "data-eng"
    try:
        svc.tasks_for_scanner("t2", scanner["id"])
    except KeyError:
        pass
    else:
        raise AssertionError("cross-tenant access must fail")
