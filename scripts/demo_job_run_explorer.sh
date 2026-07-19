#!/usr/bin/env bash
set -euo pipefail
python scripts/seed_job_run_demo.py
printf 'Job/run demo metadata prepared; start optional compose profiles for real integrations.\n'
