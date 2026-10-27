#!/usr/bin/env python3
"""Write deterministic, non-publishable image digests for Helm structure tests."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import yaml  # type: ignore[import-untyped]

COMPONENTS = (
    "api",
    "console",
    "qualityWorker",
    "scannerWorker",
    "monitorRuntime",
    "pathwayWorker",
    "kafkaObserver",
    "otelCollector",
    "migrationJob",
)


def structural_values() -> dict[str, object]:
    return {
        component: {
            "image": {
                "digest": "sha256:" + hashlib.sha256(f"dataobs-structural-validation:{component}".encode()).hexdigest()
            }
        }
        for component in COMPONENTS
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.write_text(yaml.safe_dump(structural_values(), sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
