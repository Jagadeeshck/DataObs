"""
Baseline data-quality checks for the POC pipeline.

Checks performed per dataset
-----------------------------
- row_count             : passes if at least 1 row is present
- duplicate_ratio       : warn if > 1 % duplicates
- null_pct per column   : pass < 5 %, warn 5–20 %, fail > 20 %
- schema_snapshot       : captures the column list for lineage/drift detection

Each check emits a quality result document compatible with the
``dataobs-quality-results`` index mapping used by the rest of the platform.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_sig(row: Dict[str, Any]) -> str:
    return hashlib.md5(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()


def run_basic_quality_checks(
    records: List[Dict[str, Any]],
    dataset_name: str,
    warn_null_pct: float = 5.0,
    fail_null_pct: float = 20.0,
    dup_threshold_pct: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Run baseline quality checks on *records* and return a list of quality
    result documents ready for indexing into Elasticsearch.

    Args:
        records:          List of row dicts from the parsed source.
        dataset_name:     Dataset identifier (used as ``table`` in results).
        warn_null_pct:    Null % threshold above which a column triggers a warning.
        fail_null_pct:    Null % threshold above which a column triggers a failure.
        dup_threshold_pct: Duplicate % threshold for a warning.
    """
    now = _now()
    total = len(records)
    results: List[Dict[str, Any]] = []

    # 1. Row count check
    results.append(
        {
            "check_name": "row_count",
            "table": dataset_name,
            "status": "pass" if total > 0 else "fail",
            "score": 1.0 if total > 0 else 0.0,
            "details": {"row_count": total},
            "@timestamp": now,
        }
    )

    if total == 0:
        return results

    # 2. Schema snapshot
    columns: List[str] = []
    for row in records:
        for k in row.keys():
            if k not in columns:
                columns.append(k)
    results.append(
        {
            "check_name": "schema_snapshot",
            "table": dataset_name,
            "status": "pass",
            "score": 1.0,
            "details": {"columns": columns, "column_count": len(columns)},
            "@timestamp": now,
        }
    )

    # 3. Duplicate ratio
    seen: set = set()
    duplicates = 0
    for row in records:
        sig = _row_sig(row)
        if sig in seen:
            duplicates += 1
        else:
            seen.add(sig)
    dup_pct = (duplicates / total) * 100
    results.append(
        {
            "check_name": "duplicate_ratio",
            "table": dataset_name,
            "status": "warn" if dup_pct >= dup_threshold_pct else "pass",
            "score": max(0.0, 1.0 - dup_pct / 100.0),
            "details": {"duplicates": duplicates, "total_rows": total, "dup_pct": round(dup_pct, 4)},
            "@timestamp": now,
        }
    )

    # 4. Null % per column
    for col in columns:
        null_count = sum(1 for row in records if row.get(col) in (None, "", "null", "NULL", "None", "N/A", "n/a", "NA"))
        pct = (null_count / total) * 100
        if pct >= fail_null_pct:
            status = "fail"
        elif pct >= warn_null_pct:
            status = "warn"
        else:
            status = "pass"
        results.append(
            {
                "check_name": "null_pct",
                "column": col,
                "table": dataset_name,
                "status": status,
                "score": max(0.0, 1.0 - pct / 100.0),
                "details": {"column": col, "null_count": null_count, "null_pct": round(pct, 4)},
                "@timestamp": now,
            }
        )

    return results
