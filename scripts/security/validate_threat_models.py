#!/usr/bin/env python3
import argparse
import datetime as dt
from pathlib import Path

import yaml


def validate(registry, controls, root=Path("."), today=None):
    today = today or dt.date.today()
    ids = {c["id"] for c in controls["controls"]}
    errors = []
    maxage = registry.get("review_maximum_age_days", 365)
    for x in registry.get("threat_models", []):
        key = x.get("threat_model_id", "unknown")
        doc = root / x.get("document", "")
        if not doc.is_file():
            errors.append(f"{key}:missing_document")
        for cid in x.get("relevant_controls", []):
            if cid not in ids:
                errors.append(f"{key}:unknown_control:{cid}")
        if x.get("status") == "current":
            try:
                if (today - dt.date.fromisoformat(x["last_reviewed"])).days > maxage:
                    errors.append(f"{key}:stale_review")
            except Exception:
                errors.append(f"{key}:missing_review_date")
    return errors


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registry", default="docs/security/threat-model-registry.yaml")
    p.add_argument("--controls", default="docs/security/security-controls.yaml")
    a = p.parse_args()
    e = validate(yaml.safe_load(Path(a.registry).read_text()), yaml.safe_load(Path(a.controls).read_text()))
    print("\n".join(e) if e else "threat model registry valid")
    return bool(e)


if __name__ == "__main__":
    raise SystemExit(main())
