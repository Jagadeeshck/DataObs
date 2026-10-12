#!/usr/bin/env bash
# Prepare the backend and console without storing Python dependencies in the checkout.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
tools_dir="${DATAOBS_TOOLS_DIR:-/workspace/.dataobs-tools}"
mkdir -p "$tools_dir"
tools_dir="$(cd -- "$tools_dir" && pwd -P)"
case "$tools_dir/" in
  "$repo_root/"*)
    echo "DATAOBS_TOOLS_DIR must be outside the checkout; repository tests scan its files." >&2
    exit 1
    ;;
esac

cd "$repo_root"
python -m venv "$tools_dir/venv"
source "$tools_dir/venv/bin/activate"
export PIP_CACHE_DIR="$tools_dir/pip-cache"
python -m pip install -r requirements.txt -r requirements-ci.txt
python -m pip check

npm install --cache "$tools_dir/npm-cache" --prefix "$tools_dir" pnpm@10.28.1
cd "$repo_root/ui/dataobs-console"
"$tools_dir/node_modules/.bin/pnpm" install --frozen-lockfile --store-dir "$tools_dir/pnpm-store"
"$tools_dir/node_modules/.bin/pnpm" build
