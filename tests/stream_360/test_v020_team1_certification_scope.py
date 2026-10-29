from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

TEAM1_SECURITY_WORKFLOWS = (
    ".github/workflows/stream-observer-backend.yml",
    ".github/workflows/cluster-360-console.yml",
    ".github/workflows/connector-schema-360-console.yml",
    ".github/workflows/stream-360-core-console.yml",
    ".github/workflows/pathway-explorer-console.yml",
    ".github/workflows/stream-pathway-reliability-runtime-v1.yml",
)


def test_team1_certification_excludes_team2_data_product_security_profile():
    for relative in TEAM1_SECURITY_WORKFLOWS:
        text = (ROOT / relative).read_text()
        assert "tests/security" in text
        assert "--ignore=tests/security/data_products" in text


def test_pathway_explorer_invokes_console_seeder_as_module():
    text = (ROOT / ".github/workflows/pathway-explorer-console.yml").read_text()
    assert "python -m scripts.seed_console_demo" in text
    assert "python scripts/seed_console_demo.py" not in text


def test_stream_observer_generate_and_verify_require_identical_suites():
    text = (ROOT / ".github/workflows/stream-observer-backend.yml").read_text()
    required = (
        "--required-suite elasticsearch "
        "--required-suite kafka "
        "--required-suite integration "
        "--required-suite observer "
        "--required-suite security "
        "--required-suite tenant"
    )
    assert text.count(required) == 2


def test_team1_browser_callers_install_certified_browser_matrix():
    for relative in (
        ".github/workflows/cluster-360-console.yml",
        ".github/workflows/connector-schema-360-console.yml",
        ".github/workflows/stream-360-core-console.yml",
        ".github/workflows/pathway-explorer-console.yml",
        ".github/workflows/stream-pathway-reliability-runtime-v1.yml",
    ):
        text = (ROOT / relative).read_text()
        assert "playwright install --with-deps chromium firefox webkit" in text


def test_mandatory_team1_artifacts_have_downloaded_envelope_verification():
    expected = {
        ".github/workflows/pathway-intelligence-backend.yml": (
            "pathway-intelligence-backend-v1-evidence",
            ("pathways", "tenant-isolation"),
        ),
        ".github/workflows/cluster-360-console.yml": (
            "cluster-360-console-v1-evidence",
            ("api", "browser", "accessibility"),
        ),
        ".github/workflows/connector-schema-360-console.yml": (
            "connector-schema-360-console-v1-evidence",
            ("api", "redaction", "browser"),
        ),
        ".github/workflows/stream-360-core-console.yml": (
            "stream-360-core-console-v1-evidence",
            ("api", "browser", "accessibility"),
        ),
        ".github/workflows/pathway-explorer-console.yml": (
            "pathway-explorer-console-v1-evidence",
            ("pathways", "browser", "tenant-isolation"),
        ),
    }
    for relative, (artifact, categories) in expected.items():
        text = (ROOT / relative).read_text()
        assert "verify-evidence:" in text
        assert f"name: {artifact}, path: downloaded-evidence" in text
        assert "check_downloaded_envelope.py --directory downloaded-evidence" in text
        for category in categories:
            assert f"--category {category}" in text


def test_downloaded_envelope_verifiers_have_checksum_inventory_and_bootstrap():
    for relative in (
        ".github/workflows/pathway-intelligence-backend.yml",
        ".github/workflows/cluster-360-console.yml",
        ".github/workflows/connector-schema-360-console.yml",
        ".github/workflows/stream-360-core-console.yml",
        ".github/workflows/pathway-explorer-console.yml",
    ):
        text = (ROOT / relative).read_text()
        assert "--supporting-file evidence/" in text
        assert "python -m pip install pyyaml" in text
        assert "verify_artifacts.py downloaded-evidence --sentinels-only" in text


def test_stream_observer_verifies_run_attempt_provenance():
    text = (ROOT / ".github/workflows/stream-observer-backend.yml").read_text()
    assert 'value["workflow_run_attempt"]' in text
    assert 'os.environ["GITHUB_RUN_ATTEMPT"]' in text
    assert 'value["producer_sha"] == os.environ["GITHUB_SHA"]' in text


def test_stream_observer_matches_release_manifest_categories_and_checksums():
    text = (ROOT / ".github/workflows/stream-observer-backend.yml").read_text()
    assert text.count("--required-suite integration") == 2
    assert 'item["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()' in text


def test_reliability_release_authority_workflow_retains_canonical_evidence():
    text = (ROOT / ".github/workflows/stream-pathway-reliability-production-closure-v1.yml").read_text()
    assert ".github/workflows/stream-pathway-reliability-production-closure-v1.yml" in text
    assert "--ignore=tests/security/data_products" in text
    assert "playwright install --with-deps chromium firefox webkit" in text
    assert "stream-pathway-reliability-production-closure-v1-evidence" in text
    assert "write_evidence_envelope.py --output evidence/evidence.json" in text
    assert "--test-category reliability" in text
    assert "--test-category tenant-isolation" in text
    assert "--test-category browser" in text
    assert "--test-category accessibility" in text
    assert "check_downloaded_envelope.py --directory downloaded-evidence" in text
