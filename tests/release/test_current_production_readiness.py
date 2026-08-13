from scripts.release.current_terminal_migration import migration_report
from scripts.release.render_current_production_readiness import render


def test_generated_current_state_matches_canonical_source():
    value = render()
    assert migration_report()["terminal_migration"] in value
    assert value == open("docs/release/current-production-readiness.md").read()


def test_stale_migration_and_release_sha_are_detectable():
    value = render()
    assert value.replace(migration_report()["terminal_migration"], "stale") != value
    assert value.replace("d4f511ebb331b74528426b91ce69bd24f8993eac", "0" * 40) != value
