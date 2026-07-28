from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/data-product-membership.yml")


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text())


def test_elasticsearch_service_health_commands_use_docker_safe_quoting():
    text = WORKFLOW.read_text()
    workflow = _workflow()
    service_jobs = [
        workflow["jobs"]["data-product-reconciliation-elasticsearch"],
        workflow["jobs"]["data-product-reconciliation-security"],
    ]
    for job in service_jobs:
        options = job["services"]["elasticsearch"]["options"]
        assert options.startswith('--health-cmd "curl -fsS http://localhost:9200/_cluster/health"')
        assert "--health-retries 30" in options
    assert "--health-cmd '" not in text


def test_focused_type_gate_covers_authoritative_data_product_modules():
    command = next(
        step["run"]
        for step in _workflow()["jobs"]["data-product-reconciliation-contracts"]["steps"]
        if str(step.get("run", "")).lstrip().startswith("mypy")
    )
    required = {
        "packages/domain_model/data_product.py",
        "services/data_products/repository.py",
        "services/data_products/memory_repository.py",
        "services/data_products/elasticsearch_repository.py",
        "services/data_products/elasticsearch_repository_base.py",
        "services/data_products/reconciliation.py",
        "services/data_products/service.py",
        "services/data_products/membership_service.py",
        "services/data_products/dependency_service.py",
        "services/data_products/impact.py",
        "src/api/data_product_routes.py",
    }
    assert required <= set(command.split())
    assert "src" not in command.split()


def test_diagnostic_dispatch_cannot_produce_or_validate_hosted_evidence():
    jobs = _workflow()["jobs"]
    assert jobs["data-product-reconciliation-evidence"]["if"] == "github.event_name != 'workflow_dispatch'"
    assert jobs["data-product-reconciliation-summary"]["if"] == ("always() && github.event_name != 'workflow_dispatch'")
    diagnostic = jobs["data-product-reconciliation-diagnostic-summary"]
    assert diagnostic["if"] == "always() && github.event_name == 'workflow_dispatch'"
    assert "not certification evidence" in str(diagnostic["steps"])
