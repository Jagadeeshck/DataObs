from scripts.check_merge_conflict_markers import MARKERS


def matches(line: str) -> bool:
    return any(pattern.fullmatch(line) for pattern in MARKERS)


def test_detects_standard_merge_markers() -> None:
    assert matches("<<<<<<< HEAD")
    assert matches("=======")
    assert matches(">>>>>>> origin/main")


def test_ignores_similar_non_marker_content() -> None:
    assert not matches("prefix <<<<<<< HEAD")
    assert not matches("========")
    assert not matches(">>>>>>>")
    assert not matches("normal documentation text")
