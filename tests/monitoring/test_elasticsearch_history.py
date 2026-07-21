import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from elasticsearch import ConflictError

from packages.domain_model.monitor import (
    MonitorDefinition,
    MonitorTarget,
    MonitorThresholdPolicy,
    MonitorType,
    ThresholdMode,
)
from services.monitoring.elasticsearch_repository import ElasticsearchMonitorRepository
from services.monitoring.repository import ConsistencyError


def definition(minimum: float) -> MonitorDefinition:
    return MonitorDefinition(
        id="same",
        tenant_id="tenant-a",
        monitor_type=MonitorType.VOLUME,
        target=MonitorTarget(asset_id="orders"),
        threshold=MonitorThresholdPolicy(mode=ThresholdMode.FIXED, minimum=minimum),
        managed_by="test",
        revision=1,
        etag='"etag"',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_divergent_definition_at_same_revision_is_not_an_exact_replay():
    client = Mock()
    client.create.side_effect = ConflictError("conflict", meta=Mock(status=409), body={})
    first = definition(1)
    source = ElasticsearchMonitorRepository._source(first)
    client.get.return_value = {
        "_source": {
            "tenant_id": first.tenant_id,
            "environment": first.environment,
            "monitor_id": first.id,
            "revision": first.revision,
            "etag": first.etag,
            "action": "created",
            "definition_checksum": hashlib.sha256(
                json.dumps(source, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
    }
    with pytest.raises(ConsistencyError, match="divergent"):
        ElasticsearchMonitorRepository(client).append_definition_event(definition(2), actor="alice", action="created")
