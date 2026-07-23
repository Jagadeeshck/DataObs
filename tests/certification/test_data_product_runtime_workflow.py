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
