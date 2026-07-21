import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]


def test_local_evidence_matches_schema_and_is_not_hosted():
    schema = json.loads((ROOT / "certification/evidence-manifest.schema.json").read_text())
    evidence = json.loads((ROOT / "certification/evidence/certification-evidence.json").read_text())
    jsonschema.validate(evidence, schema)
    assert evidence["workflow_run_id"] is None
