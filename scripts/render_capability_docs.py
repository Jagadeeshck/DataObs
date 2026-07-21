#!/usr/bin/env python3
"""Deterministically render capability documentation."""

from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/product"
MARK = "<!-- Generated from the machine-readable capability ledger. Do not edit manually. -->\n"


def esc(x):
    return str(x).replace("|", "\\|").replace("\n", " ")


def surfaces(c):
    i = c["implementation"]
    values = i["code_paths"] + i["api_paths"] + i["ui_routes"] + i["migrations"]
    return "<br>".join(f"`{esc(x)}`" for x in values) or "None"


def main():
    d = yaml.safe_load((OUT / "capability-ledger.yaml").read_text())
    caps = sorted(d["capabilities"], key=lambda c: (c["pillar"], c["domain"], c["id"]))
    counts = Counter(c["state"] for c in caps)
    pillars = Counter(c["pillar"] for c in caps)
    lines = (
        [
            MARK,
            "# Capability ledger",
            "",
            f"Audited commit: `{d['last_audited_commit']}` · PR range: {d['audited_pr_range']}",
            "",
            "## State counts",
            "",
        ]
        + [f"- **{k}**: {v}" for k, v in sorted(counts.items())]
        + ["", "## Pillar counts", ""]
        + [f"- **{k}**: {v}" for k, v in sorted(pillars.items())]
        + ["", "## Capabilities", ""]
    )
    for c in caps:
        lines += [
            f"### `{c['id']}` — {c['name']}",
            "",
            c["summary"],
            "",
            f"- **State:** `{c['state']}`",
            f"- **Release readiness:** `{c['release_readiness']}`",
            f"- **Next gate:** {c['next_gate']}",
            "",
        ]
    (OUT / "capability-ledger.md").write_text("\n".join(lines).rstrip() + "\n")
    table = [
        MARK,
        "# Feature matrix",
        "",
        "| Capability | State | Release readiness | Implemented surfaces | Evidence | Open blockers | Next gate |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in caps:
        ev = (
            "<br>".join(f"`{x}`" for x in c["evidence"]["tests"] + c["evidence"]["workflow_jobs"])
            or "No executed evidence retained"
        )
        table.append(
            "| "
            + " | ".join(
                map(
                    esc,
                    [
                        f"`{c['id']}` {c['name']}",
                        c["state"],
                        c["release_readiness"],
                        surfaces(c),
                        ev,
                        "; ".join(c["blockers"]) or "None",
                        c["next_gate"],
                    ],
                )
            )
            + " |"
        )
    (OUT / "feature-matrix.md").write_text("\n".join(table) + "\n")
    sections = [
        ("unit tests", "unit"),
        ("integration tests", "integration"),
        ("real-stack environments", "real_stack"),
        ("hosted CI", "hosted_ci"),
        ("browser/accessibility", "browser"),
        ("security", "security"),
        ("scale", "scale"),
        ("upgrade", "upgrade"),
        ("release", "release"),
    ]
    idx = [
        MARK,
        "# Evidence index",
        "",
        "An entry marked `defined_not_run` is a definition, not executed evidence. No hosted run is inferred from local execution.",
        "",
    ]
    for title, dim in sections:
        idx += [
            f"## {title}",
            "",
            "| Capability IDs | Path/job | Execution status | Version | Latest known run | Limitations |",
            "|---|---|---|---|---|---|",
        ]
        for c in caps:
            paths = c["evidence"]["tests"] + c["evidence"]["workflow_jobs"] or ["—"]
            idx.append(
                f"| `{c['id']}` | {', '.join(f'`{p}`' for p in paths)} | `{c['validation'][dim]}` | not recorded | none retained | {esc('; '.join(c['blockers']) or 'None')} |"
            )
        idx.append("")
    (OUT / "evidence-index.md").write_text("\n".join(idx).rstrip() + "\n")
    (ROOT / "capability-state-counts.json").write_text(
        __import__("json").dumps(dict(sorted(counts.items())), indent=2) + "\n"
    )
    print(f"rendered 3 capability documents from {len(caps)} capabilities")


if __name__ == "__main__":
    main()
