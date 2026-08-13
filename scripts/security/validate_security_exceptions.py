#!/usr/bin/env python3
import argparse
import datetime as dt
from pathlib import Path

import yaml


def validate(controls, exceptions, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    ids = {c["id"] for c in controls.get("controls", [])}
    errors = []
    for x in exceptions.get("exceptions", []):
        key = x.get("exception_id", "unknown")
        cid = x.get("control_id")
        scope = x.get("scope")
        if cid not in ids:
            errors.append(f"{key}:unknown_control")
        if cid == "*":
            errors.append(f"{key}:wildcard_control")
        if scope in ("*", "production:*"):
            errors.append(f"{key}:wildcard_production_scope")
        for field in ("owner", "approval_reference", "compensating_controls"):
            if not x.get(field):
                errors.append(f"{key}:missing_{field}")
        try:
            if dt.datetime.fromisoformat(x["expiry"].replace("Z", "+00:00")) <= now:
                errors.append(f"{key}:expired")
        except Exception:
            errors.append(f"{key}:invalid_expiry")
    return errors


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--controls", default="docs/security/security-controls.yaml")
    p.add_argument("--exceptions", default="docs/security/security-exceptions.yaml")
    a = p.parse_args()
    errors = validate(yaml.safe_load(Path(a.controls).read_text()), yaml.safe_load(Path(a.exceptions).read_text()))
    print("\n".join(errors) if errors else "security exceptions valid")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
