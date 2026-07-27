from __future__ import annotations

from pathlib import Path
import re


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}: {old!r}")
    file.write_text(text.replace(old, new, 1))


repository = "services/data_products/elasticsearch_repository.py"
replace_once(
    repository,
    '            "next_attempt_at": state.next_attempt_at.isoformat() if state.next_attempt_at else None,\n'
    '            "claim_expires_at": state.claim_expires_at.isoformat() if state.claim_expires_at else None,',
    '            "next_attempt_at": state.next_attempt_at.isoformat() if state.next_attempt_at else None,\n'
    '            "next_attempt_at_nanos": state.next_attempt_at.isoformat() if state.next_attempt_at else None,\n'
    '            "claim_expires_at": state.claim_expires_at.isoformat() if state.claim_expires_at else None,',
)
replace_once(
    repository,
    '{"range": {"next_attempt_at": {"lte": query_instant}}},',
    '{"range": {"next_attempt_at_nanos": {"lte": query_instant}}},',
)
replace_once(
    repository,
    '            sort=[{"occurred_at": "asc"}, {"operation_id": "asc"}],',
    '            sort=[\n'
    '                {"next_attempt_at_nanos": {"order": "asc", "missing": "_first"}},\n'
    '                {"operation_id": "asc"},\n'
    '            ],',
)
replace_once(
    repository,
    '            sort=[{"occurred_at": "asc"}, {"_id": "asc"}],',
    '            sort=[{"occurred_at": "asc"}, {"document.event_id": "asc"}],',
)
replace_once(
    repository,
    '\n    @staticmethod\n    def _classify_dependency_edge',
    '\n        self.client.indices.refresh(index=DEPENDENCIES)\n\n'
    '    @staticmethod\n    def _classify_dependency_edge',
)

manifest = Path("packages/elastic_store/manifest.py")
text = manifest.read_text()
pattern = re.compile(
    r'DATA_PRODUCT_CLAIM_EXPIRES_DATE_MIGRATION = Migration\(.*?\n\)\n\n\ndef migrations',
    re.DOTALL,
)
replacement = '''DATA_PRODUCT_CLAIM_EXPIRES_DATE_MIGRATION = Migration(
    "0019_data_product_operation_claim_expires_date",
    "Add nanosecond-safe claim expiry and retry scheduling fields to Data Product operation state",
    "v1",
    dependencies=["0018_data_product_decision_reason_alias"],
    rollback_strategy="stop reconciliation workers; retain the additive scheduling mappings and operation evidence",
    operations={
        "mapping_updates": {
            "dataobs-data-product-operation-state-v1": {
                "claim_expires_at": {"type": "date_nanos"},
                "next_attempt_at_nanos": {"type": "date_nanos"},
            }
        }
    },
)


def migrations'''
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit(f"manifest migration block matches: {count}")
manifest.write_text(text)

mapping_test = "tests/integration/data_products/test_migrations_elasticsearch.py"
replace_once(
    mapping_test,
    '        "next_attempt_at": "date",\n        "claim_expires_at": "date",',
    '        "next_attempt_at": "date",\n'
    '        "next_attempt_at_nanos": "date_nanos",\n'
    '        "claim_expires_at": "date_nanos",',
)

unit_test = Path("tests/data_products/test_elastic_migration_selection.py")
unit_text = unit_test.read_text()
marker = "def test_operation_schedule_precision_mapping_is_additive():"
if marker not in unit_text:
    unit_text += '''


def test_operation_schedule_precision_mapping_is_additive():
    latest = migrations()[-1]
    mapping = latest.operations["mapping_updates"]["dataobs-data-product-operation-state-v1"]
    assert latest.migration_id == "0019_data_product_operation_claim_expires_date"
    assert mapping["claim_expires_at"]["type"] == "date_nanos"
    assert mapping["next_attempt_at_nanos"]["type"] == "date_nanos"
'''
    unit_test.write_text(unit_text)

from packages.elastic_store.manifest import migrations

migration = migrations()[-1]
ledger = Path("docs/product/capability-ledger.yaml")
ledger_text = ledger.read_text()
ledger_pattern = re.compile(rf"(^  {re.escape(migration.migration_id)}: )[0-9a-f]+$", re.MULTILINE)
ledger_text, count = ledger_pattern.subn(rf"\g<1>{migration.checksum}", ledger_text, count=1)
if count != 1:
    raise SystemExit(f"capability ledger checksum matches: {count}")
ledger.write_text(ledger_text)
print(migration.migration_id, migration.checksum)
