#!/usr/bin/env bash
set -Eeuo pipefail
python -m pytest tests/certification/security tests/certification/test_security.py -q --junitxml=certification/evidence/certification-security.xml
python scripts/certification/redact_artifacts.py certification/evidence
python scripts/certification/verify_artifacts.py certification/evidence
