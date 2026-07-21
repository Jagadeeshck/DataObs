from copy import deepcopy

from scripts.validate_capability_ledger import load, validate


def errors(mutator):
    data = deepcopy(load())
    mutator(data)
    return validate(data)


def test_authoritative_ledger_is_valid():
    assert validate(load()) == []


def test_duplicate_and_invalid_ids_rejected():
    assert errors(lambda d: d["capabilities"].append(deepcopy(d["capabilities"][0])))
    assert errors(lambda d: d["capabilities"][0].update(id="INVALID"))


def test_invalid_state_rejected():
    assert errors(lambda d: d["capabilities"][0].update(state="complete"))


def test_missing_paths_tests_and_migrations_rejected():
    assert errors(lambda d: d["capabilities"][0]["implementation"]["code_paths"].append("missing.py"))
    assert errors(lambda d: d["capabilities"][0]["evidence"]["tests"].append("tests/nope.py"))
    assert errors(lambda d: d["capabilities"][0]["implementation"]["migrations"].append("9999_missing"))


def test_validated_requires_executed_evidence():
    assert errors(lambda d: d["capabilities"][0].update(state="validated"))


def test_not_started_has_no_surfaces():
    cap = next(c for c in load()["capabilities"] if c["state"] == "not_started")
    assert errors(
        lambda d: next(c for c in d["capabilities"] if c["id"] == cap["id"])["implementation"]["code_paths"].append(
            "README.md"
        )
    )


def test_optional_and_deprecated_require_guidance():
    assert errors(
        lambda d: next(c for c in d["capabilities"] if c["state"] == "optional_integration").update(summary="optional")
    )
    assert errors(lambda d: d["capabilities"][0].update(state="deprecated"))


def test_migration_checksums_are_immutable():
    assert not any("checksum" in e for e in validate(load()))
