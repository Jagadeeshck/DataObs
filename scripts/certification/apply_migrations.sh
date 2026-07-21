#!/usr/bin/env bash
set -Eeuo pipefail
python -m packages.elastic_store.cli apply
python -m packages.elastic_store.cli status
