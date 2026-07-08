from __future__ import annotations
from typing import Any, Dict

TEXT_KW = {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}}
DATAOBS_INDEX_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "dataobs-assets-v1": {"index_patterns": ["dataobs-assets-v1*"], "template": {"mappings": {"properties": {
        "asset_id": {"type": "keyword"}, "name": TEXT_KW, "asset_type": {"type": "keyword"}, "source_system": {"type": "keyword"},
        "database": {"type": "keyword"}, "schema": {"type": "keyword"}, "owner": {"type": "keyword"}, "domain": {"type": "keyword"},
        "criticality": {"type": "keyword"}, "tags": {"type": "keyword"}, "description": TEXT_KW, "created_at": {"type": "date"},
        "updated_at": {"type": "date"}, "last_seen_at": {"type": "date"}, "health_status": {"type": "keyword"}, "tenant_id": {"type":"keyword"}}}}},
    "dataobs-columns-v1": {"index_patterns": ["dataobs-columns-v1*"], "template": {"mappings": {"properties": {
        "asset_id": {"type": "keyword"}, "column_name": TEXT_KW, "data_type": {"type":"keyword"}, "nullable": {"type":"boolean"},
        "pii_flag": {"type":"boolean"}, "description": TEXT_KW, "sample_values": {"type":"keyword"}, "stats": {"type":"object", "enabled": False}, "tenant_id": {"type":"keyword"}}}}},
    "dataobs-quality-checks-v1": {"index_patterns": ["dataobs-quality-checks-v1*"], "template": {"mappings": {"properties": {
        "check_id": {"type":"keyword"}, "asset_id": {"type":"keyword"}, "check_type": {"type":"keyword"}, "metric_name": {"type":"keyword"},
        "threshold_type": {"type":"keyword"}, "threshold_value": {"type":"double"}, "severity": {"type":"keyword"}, "enabled": {"type":"boolean"},
        "owner": {"type":"keyword"}, "created_at": {"type":"date"}, "updated_at": {"type":"date"}, "tenant_id": {"type":"keyword"}}}}},
    "dataobs-quality-runs-v1": {"index_patterns": ["dataobs-quality-runs-v1*"], "template": {"mappings": {"properties": {
        "run_id": {"type":"keyword"}, "check_id": {"type":"keyword"}, "asset_id": {"type":"keyword"}, "status": {"type":"keyword"},
        "observed_value": {"type":"double"}, "expected_value": {"type":"double"}, "severity": {"type":"keyword"}, "message": TEXT_KW,
        "started_at": {"type":"date"}, "finished_at": {"type":"date"}, "duration_ms": {"type":"long"}, "tenant_id": {"type":"keyword"}}}}},
    "dataobs-job-runs-v1": {"index_patterns": ["dataobs-job-runs-v1*"], "template": {"mappings": {"properties": {
        "job_run_id": {"type":"keyword"}, "job_name": TEXT_KW, "job_type": {"type":"keyword"}, "source_system": {"type":"keyword"},
        "status": {"type":"keyword"}, "started_at": {"type":"date"}, "finished_at": {"type":"date"}, "duration_ms": {"type":"long"},
        "input_assets": {"type":"keyword"}, "output_assets": {"type":"keyword"}, "error_message": TEXT_KW, "logs_url": {"type":"keyword"}, "trace_id": {"type":"keyword"}, "tenant_id": {"type":"keyword"}}}}},
    "dataobs-lineage-edges-v1": {"index_patterns": ["dataobs-lineage-edges-v1*"], "template": {"mappings": {"properties": {
        "edge_id": {"type":"keyword"}, "source_asset_id": {"type":"keyword"}, "target_asset_id": {"type":"keyword"}, "relationship_type": {"type":"keyword"},
        "job_name": TEXT_KW, "job_run_id": {"type":"keyword"}, "observed_at": {"type":"date"}, "tenant_id": {"type":"keyword"}}}}},
    "dataobs-incidents-v1": {"index_patterns": ["dataobs-incidents-v1*"], "template": {"mappings": {"properties": {"incident_id":{"type":"keyword"}, "asset_id":{"type":"keyword"}, "status":{"type":"keyword"}, "severity":{"type":"keyword"}, "created_at":{"type":"date"}, "updated_at":{"type":"date"}, "description": TEXT_KW, "tenant_id":{"type":"keyword"}}}}},
}
