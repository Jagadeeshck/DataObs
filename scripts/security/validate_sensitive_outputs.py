#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

PATTERNS = [
    ("authorization_header", re.compile(r"(?i)authorization\s*[:=]\s*(?:bearer|basic)\s+\S+")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("cookie", re.compile(r"(?i)(?:set-)?cookie\s*[:=]")),
]


def inspect(paths):
    findings = []
    for p in paths:
        text = p.read_text(errors="ignore")
        for code, rx in PATTERNS:
            for m in rx.finditer(text):
                findings.append({"file": str(p), "line": text.count("\n", 0, m.start()) + 1, "code": code})
    return findings


def main():
    p = argparse.ArgumentParser()
    p.add_argument("paths", nargs="*", type=Path)
    p.add_argument("--output", type=Path, default=Path("secret-handling-report.json"))
    a = p.parse_args()
    files = [x for x in a.paths if x.is_file()]
    f = inspect(files)
    r = {"schema_version": "1.0", "status": "fail" if f else "pass", "finding_count": len(f), "findings": f}
    a.output.write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    print(r["status"])
    return bool(f)


if __name__ == "__main__":
    raise SystemExit(main())
