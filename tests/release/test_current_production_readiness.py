import yaml

from scripts.release.current_terminal_migration import migration_report
from scripts.release.render_current_production_readiness import render


def test_generated_current_state_matches_canonical_source():
    value = render()
    assert migration_report()["terminal_migration"] in value
    assert value == open("docs/release/current-production-readiness.md").read()


def test_stale_migration_and_release_sha_are_detectable():
    value = render()
    assert value.replace(migration_report()["terminal_migration"], "stale") != value
    candidate = yaml.safe_load(open("docs/release/first-supported-platform-candidate.yaml"))["candidate_source_sha"]
    assert value.replace(candidate, "0" * 40) != value
