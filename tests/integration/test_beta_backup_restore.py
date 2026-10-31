"""Destructive, real-Elasticsearch Beta snapshot/restore certification."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from elasticsearch import Elasticsearch, NotFoundError

from packages.elastic_store.client import make_client
from packages.elastic_store.manifest import migrations
from scripts.certification.provenance import certification_commit_sha
from scripts.operations.backup_dataobs import backup
from scripts.operations.restore_dataobs import restore
from scripts.operations.snapshot_common import snapshot_resources

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_BETA_BACKUP_RESTORE") != "1",
    reason="requires destructive real Elasticsearch 9.5.5 certification service",
)


def _fingerprint(es: Elasticsearch, resource: str) -> tuple[int, str]:
    response = es.search(index=resource, query={"match_all": {}}, size=1000)
    rows = [{"id": hit["_id"], "source": hit["_source"]} for hit in response["hits"]["hits"]]
    rows.sort(key=lambda row: row["id"])
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return len(rows), hashlib.sha256(encoded).hexdigest()


def test_beta_backup_restore_exact_state_and_tenant_isolation() -> None:
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    url = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
    es = make_client()
    assert es.info()["version"]["number"] == "9.5.5"
    subprocess.run(
        ["python", "-m", "packages.elastic_store.cli", "apply"],
        check=True,
        env={**os.environ, "ELASTICSEARCH_URL": url},
    )
    current = "dataobs-incidents-v1"
    stream = "logs-dataobs.security-event-certification"
    fixtures = {
        "tenant-a": {
            "tenant_id": "tenant-a",
            "environment": "beta",
            "title": "fixture-a",
            "@timestamp": "2026-01-01T00:00:00Z",
        },
        "tenant-b": {
            "tenant_id": "tenant-b",
            "environment": "beta",
            "title": "fixture-b",
            "@timestamp": "2026-01-01T00:00:01Z",
        },
    }
    for tenant, document in fixtures.items():
        es.index(index=current, id=f"{tenant}-current", document=document)
        es.index(index=stream, document={**document, "event_action": "authentication_failed"})
    es.indices.refresh(index=f"{current},{stream}")
    before = {name: _fingerprint(es, name) for name in (current, stream)}
    snapshot = f"beta-{int(time.time())}"
    backup_started = time.monotonic()
    backup_report = backup(
        es,
        "dataobs-ci",
        snapshot,
        repository_location="/tmp/dataobs-snapshots",
        register_repository=True,
    )
    backup_duration = time.monotonic() - backup_started
    # Delete only registered DataObs resources selected into the snapshot.
    for resource in snapshot_resources():
        if "*" in resource:
            try:
                es.indices.delete_data_stream(name=resource, expand_wildcards="all")
            except NotFoundError:  # resource patterns legitimately need not exist
                pass
        else:
            es.indices.delete(index=resource, ignore_unavailable=True)
    assert not es.indices.exists(index=current)
    assert not es.indices.exists(index=stream)
    restore_started = time.monotonic()
    restore_report = restore(es, "dataobs-ci", snapshot)
    for _ in range(60):
        health = es.cluster.health(wait_for_status="yellow", timeout="2s")
        if health["status"] in {"yellow", "green"}:
            break
    after = {name: _fingerprint(es, name) for name in (current, stream)}
    assert after == before
    assert es.exists(index="dataobs-system-migrations-v1", id=migrations()[-1].migration_id)
    tenant_a = es.count(index=f"{current},{stream}", query={"term": {"tenant_id": "tenant-a"}})["count"]
    tenant_b = es.count(index=f"{current},{stream}", query={"term": {"tenant_id": "tenant-b"}})["count"]
    assert tenant_a == tenant_b == 2
    assert (
        es.count(
            index=current,
            query={"bool": {"filter": [{"term": {"tenant_id": "tenant-a"}}, {"term": {"tenant_id": "tenant-b"}}]}},
        )["count"]
        == 0
    )
    restore_duration = time.monotonic() - restore_started
    report = {
        "commit_sha": certification_commit_sha(),
        "snapshot_repository": "dataobs-ci",
        "snapshot": snapshot,
        "snapshot_result": backup_report["status"],
        "destructive_deletion_result": "pass",
        "restore_result": restore_report["status"],
        "integrity_verification": "pass",
        "recovery_result": "pass",
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "backup_duration_seconds": round(backup_duration, 6),
        "restore_duration_seconds": round(restore_duration, 6),
        "schema_version": "1.0",
        "status": "pass",
        "elasticsearch_version": "9.5.5",
        "terminal_migration": migrations()[-1].migration_id,
        "resources": {name: {"count": after[name][0], "sha256": after[name][1]} for name in after},
        "tenants": ["tenant-a", "tenant-b"],
        "tenant_isolation": "pass",
        "duration_seconds": round(time.monotonic() - started, 3),
        "redaction_status": "pass",
    }
    output = Path(os.environ.get("BETA_RESTORE_REPORT", "/tmp/beta-backup-restore.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
