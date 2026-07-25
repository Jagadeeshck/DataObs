#!/usr/bin/env bash
set -Eeuo pipefail
RUN_CERTIFICATION_TESTS=1 python -m pytest tests/certification -q --ignore=tests/certification/security --junitxml=certification/evidence/certification-backend.xml
