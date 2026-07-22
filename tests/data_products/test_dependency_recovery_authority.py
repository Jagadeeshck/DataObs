from pathlib import Path

from services.data_products.reconciliation import DependencyReplacementReconciliationHandler


def test_dependency_service_has_no_second_mutation_recovery_path() -> None:
    source = Path("services/data_products/dependency_service.py").read_text()
    assert "def recover_dependency_operation" not in source
    assert "apply_dependency_mutation_plan(" not in source
    assert "finish_operation(" not in source


def test_dependency_repair_is_claim_bounded() -> None:
    assert 100 <= DependencyReplacementReconciliationHandler.CHUNK_SIZE <= 250
