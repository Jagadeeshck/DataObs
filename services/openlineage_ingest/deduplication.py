import hashlib
import json
from typing import Any, Dict


def deterministic_event_id(payload: Dict[str, Any], source_id: str) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(f"{source_id}\0{canonical}".encode()).hexdigest()
