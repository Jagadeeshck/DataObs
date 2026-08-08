import json
from pathlib import Path

path = Path("artifacts/team-4-postgresql-relational-db-foundation-v1-evidence/evidence.json")
data = json.loads(path.read_text())
required = {
    "team",
    "status",
    "base_sha",
    "repository_sha",
    "workflow",
    "workflow_run",
    "python_version",
    "postgresql_versions",
    "psycopg_version",
    "provider_version",
    "terminal_migration",
    "supported_capabilities",
    "results",
    "known_limitations",
    "independent_verification",
}
assert required <= data.keys()
assert data["team"] == "Team 4" and data["status"] == "functional_unvalidated"
assert data["provider_version"] == "1" and data["postgresql_versions"]["19_beta"] == "unsupported"
assert data["results"]["live_postgresql"] != "passed"
print("PostgreSQL foundation evidence independently verified")
