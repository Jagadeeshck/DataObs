#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.platform_lifecycle.schema_compatibility import compare_openapi, compare_schema


def main():
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=["configuration", "openapi"])
    p.add_argument("previous")
    p.add_argument("candidate")
    p.add_argument("--output")
    a = p.parse_args()
    report = (compare_openapi if a.kind == "openapi" else compare_schema)(
        json.loads(Path(a.previous).read_text()), json.loads(Path(a.candidate).read_text())
    )
    data = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if a.output:
        Path(a.output).write_text(data)
    else:
        print(data, end="")
    return report["classification"] == "breaking"


if __name__ == "__main__":
    raise SystemExit(main())
