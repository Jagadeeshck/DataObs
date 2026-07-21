import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_generated_headers_and_required_matrix_columns():
    mark = "<!-- Generated from the machine-readable capability ledger. Do not edit manually. -->"
    for name in ["capability-ledger.md", "evidence-index.md", "feature-matrix.md"]:
        assert (ROOT / "docs/product" / name).read_text().startswith(mark)
    matrix = (ROOT / "docs/product/feature-matrix.md").read_text()
    for name in [
        "Capability",
        "State",
        "Release readiness",
        "Implemented surfaces",
        "Evidence",
        "Open blockers",
        "Next gate",
    ]:
        assert name in matrix


def test_renderer_is_deterministic_and_clean():
    files = [ROOT / "docs/product" / x for x in ["capability-ledger.md", "evidence-index.md", "feature-matrix.md"]]
    before = [x.read_bytes() for x in files]
    subprocess.run([sys.executable, "scripts/render_capability_docs.py"], cwd=ROOT, check=True)
    assert before == [x.read_bytes() for x in files]
