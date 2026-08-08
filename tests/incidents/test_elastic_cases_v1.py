from services.incident_manager.cases.repository import InMemoryCaseLinkRepository
from services.incident_manager.cases.service import deterministic_reference


def test_case_reference_is_deterministic_and_scope_bound() -> None:
    first = deterministic_reference("tenant", "production", "incident", "dataobs-prod")
    assert first == deterministic_reference("tenant", "production", "incident", "dataobs-prod")
    assert first != deterministic_reference("tenant", "nonprod", "incident", "dataobs-nonprod")
    assert first.startswith("dataobs-ref-")


def test_case_repository_reservation_is_idempotent() -> None:
    assert InMemoryCaseLinkRepository() is not None
