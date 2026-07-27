from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# Running a file under .github/scripts makes that directory sys.path[0].
# Add the repository root explicitly before importing DataObs packages.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))


def replace_if_needed(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text()
    if new in text:
        print(f"{path}: already applied")
        return
    if old not in text:
        raise SystemExit(f"{path}: neither old nor new contract found: {old!r}")
    file.write_text(text.replace(old, new, 1))
    print(f"{path}: patched")


repository = "services/data_products/elasticsearch_repository.py"
replace_if_needed(
    repository,
    '            "next_attempt_at": state.next_attempt_at.isoformat() if state.next_attempt_at else None,\n'
    '            "claim_expires_at": state.claim_expires_at.isoformat() if state.claim_expires_at else None,',
    '            "next_attempt_at": state.next_attempt_at.isoformat() if state.next_attempt_at else None,\n'
    '            "next_attempt_at_nanos": state.next_attempt_at.isoformat() if state.next_attempt_at else None,\n'
    '            "claim_expires_at": state.claim_expires_at.isoformat() if state.claim_expires_at else None,',
)
replace_if_needed(
    repository,
    '{"range": {"next_attempt_at": {"lte": query_instant}}},',
    '{"range": {"next_attempt_at_nanos": {"lte": query_instant}}},',
)
replace_if_needed(
    repository,
    '            sort=[{"occurred_at": "asc"}, {"operation_id": "asc"}],',
    '            sort=[\n'
    '                {"next_attempt_at_nanos": {"order": "asc", "missing": "_first"}},\n'
    '                {"operation_id": "asc"},\n'
    '            ],',
)
replace_if_needed(
    repository,
    '            sort=[{"occurred_at": "asc"}, {"_id": "asc"}],',
    '            sort=[{"occurred_at": "asc"}, {"document.event_id": "asc"}],',
)
replace_if_needed(
    repository,
    '\n    @staticmethod\n    def _classify_dependency_edge',
    '\n        self.client.indices.refresh(index=DEPENDENCIES)\n\n'
    '    @staticmethod\n    def _classify_dependency_edge',
)

manifest = Path("packages/elastic_store/manifest.py")
manifest_text = manifest.read_text()
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
if '"next_attempt_at_nanos": {"type": "date_nanos"}' not in manifest_text:
    pattern = re.compile(
        r'DATA_PRODUCT_CLAIM_EXPIRES_DATE_MIGRATION = Migration\(.*?\n\)\n\n\ndef migrations',
        re.DOTALL,
    )
    manifest_text, count = pattern.subn(replacement, manifest_text, count=1)
    if count != 1:
        raise SystemExit(f"manifest migration block matches: {count}")
    manifest.write_text(manifest_text)
    print("packages/elastic_store/manifest.py: patched")
else:
    print("packages/elastic_store/manifest.py: already applied")

mapping_test = "tests/integration/data_products/test_migrations_elasticsearch.py"
replace_if_needed(
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
    unit_test.write_text(
        unit_text
        + '''


def test_operation_schedule_precision_mapping_is_additive():
    latest = migrations()[-1]
    mapping = latest.operations["mapping_updates"]["dataobs-data-product-operation-state-v1"]
    assert latest.migration_id == "0019_data_product_operation_claim_expires_date"
    assert mapping["claim_expires_at"]["type"] == "date_nanos"
    assert mapping["next_attempt_at_nanos"]["type"] == "date_nanos"
'''
    )
    print(f"{unit_test}: patched")
else:
    print(f"{unit_test}: already applied")

# Import after rewriting the manifest so the ledger records the exact new checksum.
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

python_files = [
    repository,
    "packages/elastic_store/manifest.py",
    mapping_test,
    str(unit_test),
]
commit_files = [*python_files, "docs/product/capability-ledger.yaml"]
subprocess.run(["black", *python_files], check=True)
subprocess.run(["git", "config", "user.name", "dataobs-ci"], check=True)
subprocess.run(["git", "config", "user.email", "dataobs-ci@users.noreply.github.com"], check=True)
subprocess.run(["git", "add", *commit_files], check=True)
if subprocess.run(["git", "diff", "--cached", "--quiet"], check=False).returncode == 0:
    print("focused runtime fix already committed")
else:
    subprocess.run(
        ["git", "commit", "-m", "fix: restore nanosecond scheduling and search visibility"],
        check=True,
    )
    head_ref = os.environ.get("HEAD_REF", "codex/restore-hosted-certification-for-dataobs")
    subprocess.run(["git", "push", "origin", f"HEAD:{head_ref}"], check=True)
