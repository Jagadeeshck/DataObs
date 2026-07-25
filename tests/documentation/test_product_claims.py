from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_readme_six_pillar_and_console_truth():
    text = (ROOT / "README.md").read_text()
    for pillar in ["Platform", "Data Pipeline", "Data", "FinOps and Cost", "Business", "AI and Agent"]:
        assert pillar in text
    assert "A React Console exists" in text
    assert "not a production release" in text
    assert "Autonomous remediation is not enabled" in text


def test_stale_phrases_absent_from_active_docs():
    stale = [
        "DataObs follows a 4-pillar model",
        "future DataObs Console",
        "DATAOBS_BACKEND=all as a normal product mode",
        "OpenSearch/Grafana as equal authoritative planes",
        "autonomous remediation enabled",
        "DataObs is production-ready",
    ]
    for path in [ROOT / "README.md", ROOT / "docs/product/README.md", ROOT / "docs/product/roadmap-v1.md"]:
        assert not any(x in path.read_text() for x in stale)


def test_issue_triage_complete():
    text = (ROOT / "docs/product/open-issue-triage.md").read_text()
    for issue in [24, 25, 28, 29, 30, 31, 32, 46, 47, 48, 49, 50, 51]:
        assert "#" + str(issue) in text


def test_roadmap_phases_complete():
    text = (ROOT / "docs/product/roadmap-v1.md").read_text()
    for phase in "ABCDEF":
        assert f"Phase {phase}" in text
    for field in [
        "Current state",
        "Entry criteria",
        "Deliverables",
        "Evidence gate",
        "Exit criteria",
        "Dependencies",
        "Non-goals",
    ]:
        assert text.count(field) >= 6


def test_canonical_pillars_exact():
    data = yaml.safe_load((ROOT / "docs/product/capability-ledger.yaml").read_text())
    assert data["canonical_pillars"] == ["platform", "data_pipeline", "data", "finops_cost", "business", "ai_agent"]
