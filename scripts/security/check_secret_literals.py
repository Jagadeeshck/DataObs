#!/usr/bin/env python3
"""Scan source fixtures and packaging without rejecting known synthetic sentinels."""

import re
from pathlib import Path

PATTERN = re.compile(r'Bearer\s+[A-Za-z0-9._-]+|client_secret:\s+[^{$"\s]+|private_key:\s+[^{$"\s]+')
# Exact fixture/path pairs, not directory exclusions. Each is an intentionally
# adversarial test or a bounded fake authentication fixture. New values fail.
SYNTHETIC = {
    ("tests/test_api_endpoints.py", "Bearer t"),
    ("tests/integrations/test_sdk.py", "Bearer bad"),
    ("tests/incidents/test_safe_remediation_closure.py", "Bearer fake-token-value-12345"),
    ("tests/security/test_beta_security_hardening.py", "Bearer abc"),
    ("tests/security/test_security_posture_v1.py", "Bearer abcdefghijklmnopqrstuvwxyz"),
}


def main():
    findings = []
    for root in ("tests", "docs", "helm/dataobs"):
        for path in Path(root).rglob("*"):
            if not path.is_file() or "node_modules" in path.parts or "__pycache__" in path.parts:
                continue
            text = path.read_text(errors="ignore")
            for match in PATTERN.finditer(text):
                if (path.as_posix(), match.group()) not in SYNTHETIC:
                    findings.append(
                        f"{path}:{text.count(chr(10), 0, match.start()) + 1}: unexpected credential-like literal"
                    )
    if findings:
        raise SystemExit("\n".join(findings))
    print("credential-like literal scan: passed (exact synthetic fixtures retained)")


if __name__ == "__main__":
    main()
