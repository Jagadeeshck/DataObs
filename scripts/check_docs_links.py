#!/usr/bin/env python3
"""Check repository-relative Markdown links."""

import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
bad = []
for doc in root.rglob("*.md"):
    if ".git" in doc.parts or "node_modules" in doc.parts:
        continue
    for link in re.findall(r"\[[^]]+\]\(([^)]+)\)", doc.read_text(errors="ignore")):
        target = link.split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if not (doc.parent / target).resolve().exists():
            bad.append(f"{doc.relative_to(root)}: {link}")
Path("broken-link-report.txt").write_text("\n".join(bad) + ("\n" if bad else "No broken repository-relative links.\n"))
print("documentation links:", "clean" if not bad else f"{len(bad)} broken")
if bad:
    print(*bad, sep="\n")
    sys.exit(1)
