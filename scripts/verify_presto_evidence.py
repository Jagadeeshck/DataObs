import json
import sys

p = json.load(open(sys.argv[1], encoding="utf-8"))
required = {
    "repository",
    "exact_sha",
    "workflow_run_id",
    "python_version",
    "presto_server_version",
    "presto_python_client_version",
    "provider_version",
    "terminal_migration",
    "sql_safety",
    "next_uri_safety",
    "status",
    "known_limitations",
}
missing = required - set(p)
if missing:
    raise SystemExit("missing evidence: " + ",".join(sorted(missing)))
if p["status"] != "functional_unvalidated" or len(p["exact_sha"]) != 40:
    raise SystemExit("invalid evidence status or SHA")
print("Presto evidence envelope verified")
