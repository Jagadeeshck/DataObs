#!/usr/bin/env python3
"""Safety controller for destructive certification operations."""

import argparse
import re
from urllib.parse import urlparse


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--opt-in", required=True)
    p.add_argument("--environment", required=True)
    p.add_argument("--synthetic-marker", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--elasticsearch-url", required=True)
    p.add_argument("--allow-elasticsearch-host", required=True)
    p.add_argument("--kube-context", required=True)
    p.add_argument("--maximum-duration", type=int, required=True)
    p.add_argument("--cleanup-plan", required=True)
    a = p.parse_args()
    host = (urlparse(a.elasticsearch_url).hostname or "").lower()
    unsafe = (
        a.opt_in != "I_UNDERSTAND_DESTRUCTIVE_TEST_ONLY"
        or a.environment not in {"test", "disposable"}
        or not a.synthetic_marker.startswith("synthetic-")
        or not re.fullmatch(r"[0-9a-f]{40}", a.sha)
        or not host
        or host != a.allow_elasticsearch_host.lower()
        or any(x in host for x in ("*", "prod", "customer"))
        or "*" in a.kube_context
        or any(x in a.kube_context.lower() for x in ("prod", "customer"))
        or not 0 < a.maximum_duration <= 28800
        or not a.cleanup_plan.strip()
    )
    if unsafe:
        p.error("unsafe target: destructive certification guard rejected request")
    print("safety guard passed for exact disposable target")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
