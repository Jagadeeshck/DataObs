import re
from pathlib import Path

import yaml

from packages.elastic_store.manifest import (
    DATA_PRODUCT_FOUNDATION_EVIDENCE_OWNERS,
    DATA_PRODUCT_FOUNDATION_JUNIT_EVIDENCE,
    DATA_PRODUCT_FOUNDATION_JUNIT_POLICIES,
)

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


def test_every_workflow_elastic_subcommand_is_supported():
    text = Path(".github/workflows/data-product-runtime.yml").read_text()
    commands = re.findall(r"(?:\./bin/)?dataobs elastic ([a-z-]+)", text)
    assert commands
    assert set(commands) <= {"plan", "apply", "status", "rollback"}
    assert "migrate" not in commands


def test_foundation_jobs_execute_truthful_suites_and_migration_order():
    workflow = yaml.safe_load(Path(".github/workflows/data-product-runtime.yml").read_text())
    jobs = workflow["jobs"]
    unit = str(jobs["data-product-reconciliation-unit"])
    elastic = str(jobs["data-product-foundation-elasticsearch"])
    security = str(jobs["data-product-foundation-security"])
    assert "tests/data_products tests/certification" in unit
    assert elastic.index("test_migrations_elasticsearch.py") < elastic.index("test_operation_state_elasticsearch.py")
    assert "DATA_PRODUCT_ALLOW_DESTRUCTIVE_TEST_RESET=1" in elastic
    assert "DATA_PRODUCT_ALLOW_DESTRUCTIVE_TEST_RESET" not in security
    assert "./bin/dataobs elastic apply" in security
    assert "wrong-scope claim mutation denial" in security
    assert "--sentinels-only artifacts/foundation" in security


def test_producer_junit_inventory_and_dependencies_are_exact():
    workflow = yaml.safe_load(Path(".github/workflows/data-product-runtime.yml").read_text())
    jobs = workflow["jobs"]
    emitted = set(re.findall(r"--junitxml=artifacts/foundation/([\w.-]+)", str(jobs)))
    owned_junit = {
        name for values in DATA_PRODUCT_FOUNDATION_EVIDENCE_OWNERS.values() for name in values if name.endswith(".xml")
    }
    assert emitted == owned_junit == set(DATA_PRODUCT_FOUNDATION_JUNIT_EVIDENCE)
    assert emitted == set(DATA_PRODUCT_FOUNDATION_JUNIT_POLICIES)
    producers = {
        "data-product-reconciliation-contracts",
        "data-product-reconciliation-unit",
        "data-product-foundation-elasticsearch",
        "data-product-foundation-security",
    }
    assert set(jobs["data-product-foundation-evidence"]["needs"]) == producers
    assert set(jobs["data-product-foundation-summary"]["needs"]) == producers | {"data-product-foundation-evidence"}
