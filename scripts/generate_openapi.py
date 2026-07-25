#!/usr/bin/env python3
"""Generate the checked-in OpenAPI contract deterministically."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.api.app import create_app  # noqa: E402

Path("openapi.json").write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n")
print("generated openapi.json")
