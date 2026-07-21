from scripts.check_migration_immutability import check


def migration(mid, checksum, dependencies=()):
    return {"migration_id": mid, "checksum": checksum, "dependencies": list(dependencies)}


def test_append_only_migration_is_allowed():
    old = [migration("0001_a", "one")]
    assert check(old, old + [migration("0002_b", "two", ["0001_a"])]) == []


def test_checksum_mutation_is_rejected_by_id():
    errors = check([migration("0001_a", "one")], [migration("0001_a", "changed")])
    assert errors == ["migration checksum changed: 0001_a"]


def test_disappearance_and_reordering_are_rejected():
    old = [migration("0001_a", "one"), migration("0002_b", "two", ["0001_a"])]
    errors = check(old, list(reversed(old)))
    assert any("order changed" in error for error in errors)
