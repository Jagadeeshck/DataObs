from pathlib import Path

import yaml

REQUIRED_PATHS = {
    "services/data_products/**",
    "packages/domain_model/data_product.py",
    "packages/elastic_store/**",
    "tests/data_products/**",
    "tests/integration/data_products/**",
    "tests/security/data_products/**",
    "tests/certification/**",
    "scripts/certification/**",
    "docs/development/data-product-reconciliation-runtime-closure.md",
    "docs/product/capability-ledger.yaml",
    ".github/workflows/data-product-runtime.yml",
}


def test_data_product_runtime_trigger_covers_every_certification_surface():
    workflow = yaml.safe_load(Path(".github/workflows/data-product-runtime.yml").read_text())
    # PyYAML 1.1 parses the YAML key `on` as boolean True.
    trigger = workflow.get("on", workflow.get(True))
    assert set(trigger["pull_request"]["paths"]) == REQUIRED_PATHS


def test_foundation_workflow_has_explicit_profile_and_required_jobs():
    text = Path(".github/workflows/data-product-runtime.yml").read_text()
    workflow = yaml.safe_load(text)
    assert workflow["name"] == "Data Product hosted certification foundation"
    assert set(workflow["jobs"]) == {
        "data-product-reconciliation-contracts",
        "data-product-reconciliation-unit",
        "data-product-foundation-elasticsearch",
        "data-product-foundation-security",
        "data-product-foundation-evidence",
        "data-product-foundation-summary",
    }
    assert "DATA_PRODUCT_CERTIFICATION_PROFILE=data-product-runtime-foundation" in text
    assert "--profile data-product-runtime-foundation" in text
    assert "continue-on-error" not in text and "|| true" not in text
