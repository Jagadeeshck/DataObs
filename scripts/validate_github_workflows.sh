#!/usr/bin/env bash
set -Eeuo pipefail
actionlint .github/workflows/*.yml
