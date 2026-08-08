import hashlib
import json


def structural_fingerprint(evidence) -> str:
    safe = [
        {k: v for k, v in item.items() if k not in {"observed_at", "owner", "comment", "default", "expression", "sql"}}
        for item in evidence
    ]
    canonical = json.dumps(
        sorted(safe, key=lambda x: json.dumps(x, sort_keys=True, default=str)),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
