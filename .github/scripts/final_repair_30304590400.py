from __future__ import annotations

import re
import subprocess
from pathlib import Path


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
    '            "claim_expires_at": state.claim_expires_at.isoformat() if state.claim_expires_at else None,\n'
    '            "claim_expires_at_nanos": state.claim_expires_at.isoformat() if state.claim_expires_at else None,',
)
replace_once(
    repository,
    '{"range": {"claim_expires_at": {"lte": query_instant}}},',
    '{"range": {"claim_expires_at_nanos": {"lte": query_instant}}},',
)
replace_once(
    repository,
    '{"bool": {"must_not": {"exists": {"field": "next_attempt_at"}}}},',
    '{"bool": {"must_not": {"exists": {"field": "next_attempt_at_nanos"}}}},',
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
manifest_text = manifest.read_text()
new_migration = '''

DATA_PRODUCT_OPERATION_SCHEDULE_NANOS_MIGRATION = Migration(
    "0020_data_product_operation_schedule_nanos",
    "Add nanosecond-safe retry and claim-expiry fields to Data Product operation state",
    "v1",
    dependencies=["0019_data_product_operation_claim_expires_date"],
    rollback_strategy="stop reconciliation workers; retain additive scheduling fields and operation evidence",
    operations={
        "mapping_updates": {
            "dataobs-data-product-operation-state-v1": {
                "next_attempt_at_nanos": {"type": "date_nanos"},
                "claim_expires_at_nanos": {"type": "date_nanos"},
            }
        }
    },
)
'''
marker = "\n\n\ndef migrations() -> List[Migration]:"
if marker not in manifest_text:
    raise SystemExit("manifest migrations marker missing")
manifest_text = manifest_text.replace(marker, new_migration + marker, 1)
list_marker = "        DATA_PRODUCT_CLAIM_EXPIRES_DATE_MIGRATION,\n    ]"
if list_marker not in manifest_text:
    raise SystemExit("manifest migration list marker missing")
manifest_text = manifest_text.replace(
    list_marker,
    "        DATA_PRODUCT_CLAIM_EXPIRES_DATE_MIGRATION,\n"
    "        DATA_PRODUCT_OPERATION_SCHEDULE_NANOS_MIGRATION,\n"
    "    ]",
    1,
)
manifest.write_text(manifest_text)

migration_test = Path("tests/integration/data_products/test_migrations_elasticsearch.py")
test_text = migration_test.read_text()
replacements = {
    'range(1, 20)]\n    assert expected[-1].migration_id == "0019_data_product_operation_claim_expires_date"':
        'range(1, 21)]\n    assert expected[-1].migration_id == "0020_data_product_operation_schedule_nanos"',
    'def test_upgrade_from_0017_executes_0018_once(':
        'def test_upgrade_from_0017_executes_later_migrations_once(',
    '"released 0017 state upgraded through 0018"':
        '"released 0017 state upgraded through latest migration"',
    '"0017 prefix applied and 0018 was initially absent"':
        '"0017 prefix applied and later migrations were initially absent"',
    '"0018 applied once without changing legacy decision evidence"':
        '"later migrations applied once without changing legacy decision evidence"',
    '        "claim_expires_at": "date",\n        "document": "flattened",':
        '        "claim_expires_at": "date",\n'
        '        "next_attempt_at_nanos": "date_nanos",\n'
        '        "claim_expires_at_nanos": "date_nanos",\n'
        '        "document": "flattened",',
}
for old, new in replacements.items():
    if test_text.count(old) != 1:
        raise SystemExit(f"migration test replacement mismatch: {old!r}")
    test_text = test_text.replace(old, new, 1)
migration_test.write_text(test_text)

unit_test = Path("tests/data_products/test_elastic_migration_selection.py")
unit_text = unit_test.read_text()
unit_text += '''


def test_operation_schedule_precision_mapping_is_additive():
    latest = migrations()[-1]
    mapping = latest.operations["mapping_updates"]["dataobs-data-product-operation-state-v1"]
    assert latest.migration_id == "0020_data_product_operation_schedule_nanos"
    assert mapping["claim_expires_at_nanos"]["type"] == "date_nanos"
    assert mapping["next_attempt_at_nanos"]["type"] == "date_nanos"
'''
unit_test.write_text(unit_text)

# Import only after the manifest contains the additive migration.
from packages.elastic_store.manifest import migrations

latest = migrations()[-1]
ledger = Path("docs/product/capability-ledger.yaml")
ledger_text = ledger.read_text()
match = re.search(
    r"^  0019_data_product_operation_claim_expires_date: [0-9a-f]+$",
    ledger_text,
    re.MULTILINE,
)
if not match:
    raise SystemExit("0019 checksum line missing")
ledger_text = ledger_text[: match.end()] + f"\n  {latest.migration_id}: {latest.checksum}" + ledger_text[match.end() :]
ledger.write_text(ledger_text)

membership = Path(".github/workflows/data-product-membership.yml")
membership_text = membership.read_text().replace("  contents: write\n", "  contents: read\n", 1)
start = membership_text.find("      - name: Apply focused Elasticsearch 9.4.2 runtime fix\n")
end = membership_text.find("      - run: python scripts/check_generated_artifacts.py\n", start)
if start < 0 or end < 0:
    raise SystemExit("temporary membership workflow block missing")
membership.write_text(membership_text[:start] + membership_text[end:])

for temporary in (
    ".github/scripts/fix_run_30304590400.py",
    ".github/scripts/final_repair_30304590400.py",
    ".github/fix-run-30304590400-request.md",
    ".github/final-repair-trigger",
    ".github/workflows/one-time-fix-run-30304590400.yml",
):
    Path(temporary).unlink(missing_ok=True)

python_files = [
    repository,
    "packages/elastic_store/manifest.py",
    "tests/integration/data_products/test_migrations_elasticsearch.py",
    "tests/data_products/test_elastic_migration_selection.py",
]
subprocess.run(["black", *python_files], check=True)
subprocess.run(["ruff", "check", *python_files], check=True)
subprocess.run(["python", "scripts/check_migration_immutability.py", "--base-ref", "origin/main"], check=True)
subprocess.run(["python", "scripts/validate_capability_ledger.py"], check=True)
subprocess.run(
    ["python", "-m", "pytest", "tests/data_products/test_elastic_migration_selection.py", "-q"],
    check=True,
)
subprocess.run(["python", "-m", "compileall", "-q", repository, "packages/elastic_store/manifest.py"], check=True)
subprocess.run(["git", "config", "user.name", "dataobs-ci"], check=True)
subprocess.run(["git", "config", "user.email", "dataobs-ci@users.noreply.github.com"], check=True)
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-m", "fix: complete hosted foundation runtime repair"], check=True)
subprocess.run(["git", "push", "origin", "HEAD:fix/run-30304590400-final"], check=True)
