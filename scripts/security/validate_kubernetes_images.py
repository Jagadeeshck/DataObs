#!/usr/bin/env python3
"""Validate immutable Kubernetes image identities without exposing credentials."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

DIGEST = re.compile(r"^sha256:([0-9a-f]{64})$")


def check_image(image: str, allowed: list[str]) -> list[str]:
    errors = []
    safe = image.rsplit("@", 1)[0].split("/")[-1]
    if "@" not in image:
        errors.append(f"{safe}: mutable tag-only image")
    else:
        name, digest = image.rsplit("@", 1)
        m = DIGEST.fullmatch(digest)
        if not m:
            errors.append(f"{safe}: invalid sha256 digest")
        elif len(set(m.group(1))) == 1:
            errors.append(f"{safe}: placeholder digest")
        registry = name.split("/", 1)[0] if "/" in name else ""
        if not registry or ("." not in registry and ":" not in registry and registry != "localhost"):
            errors.append(f"{safe}: implicit or empty registry")
        elif allowed and not any(re.fullmatch(p, registry) for p in allowed):
            errors.append(f"{safe}: registry is not allowlisted")
    if image.split("@", 1)[0].endswith(":latest"):
        errors.append(f"{safe}: latest tag forbidden")
    return errors


def images(doc):
    spec = doc.get("spec", {})
    kind = doc.get("kind")
    if kind in {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job"}:
        pod = spec.get("template", {}).get("spec", {})
    elif kind == "CronJob":
        pod = spec.get("jobTemplate", {}).get("spec", {}).get("template", {}).get("spec", {})
    elif kind == "Pod":
        pod = spec
    else:
        return []
    return [c.get("image", "") for key in ("initContainers", "containers") for c in pod.get(key, []) if c.get("image")]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("manifest")
    p.add_argument("--allowed-registry", action="append", default=[])
    p.add_argument("--report")
    a = p.parse_args(argv)
    errors = []
    for d in yaml.safe_load_all(Path(a.manifest).read_text()):
        if isinstance(d, dict):
            for image in images(d):
                errors += check_image(image, a.allowed_registry)
    report = {"status": "PASS" if not errors else "FAIL", "violations": errors}
    if a.report:
        Path(a.report).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
