import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
required = {
    "repository",
    "exact_sha",
    "workflow",
    "run_id",
    "python_version",
    "terminal_migration",
    "provider_version",
    "checks",
    "known_limitations",
}
missing = required - set(data)
if missing:
    raise SystemExit(f"missing evidence fields: {sorted(missing)}")
if data["provider_version"] != "1" or data["checks"].get("no_business_rows") != "passed":
    raise SystemExit("invalid evidence")
print("Trino evidence envelope verified independently")
