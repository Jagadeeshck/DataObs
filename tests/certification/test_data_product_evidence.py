from datetime import datetime, timezone

import pytest

from scripts.certification.data_product_evidence import write_scenario


def test_scenario_writer_records_the_executing_test(tmp_path):
    now = datetime.now(timezone.utc)
    target = write_scenario(
        tmp_path,
        filename="migration-clean-install.json",
        scenario="clean install",
        elasticsearch_version="9.4.2",
        test_names=["test_scenario_writer_records_the_executing_test"],
        assertion_summary=["latest migration exists"],
        redacted_references=[],
        started_at=now,
        completed_at=now,
        result="passed",
    )
    assert '"schema_version": "1.0"' in target.read_text()


def test_scenario_writer_rejects_placeholder_evidence(tmp_path):
    with pytest.raises(ValueError, match="non-empty"):
        write_scenario(
            tmp_path,
            filename="empty.json",
            scenario="",
            elasticsearch_version="9.4.2",
            test_names=[],
            assertion_summary=[],
            redacted_references=[],
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T00:00:00Z",
            result="passed",
        )
