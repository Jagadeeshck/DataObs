#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE=(docker compose -f "$ROOT/docker-compose.certification.yml")
profile="${CERTIFICATION_PROFILE:-core}"
command="${1:-help}"; shift || true
case "$command" in
  config) "${COMPOSE[@]}" --profile "${1:-$profile}" config ;;
  up) profile="${1:-$profile}"; "$ROOT/scripts/certification/bootstrap.sh"; "${COMPOSE[@]}" --profile "$profile" up -d --build; "$ROOT/scripts/certification/wait_for_stack.sh" "$profile" ;;
  seed) "$ROOT/scripts/certification/seed.sh" ;;
  test)
    suite="${1:?test requires backend, browser, or security}"
    case "$suite" in backend|browser|security) "$ROOT/scripts/certification/run_${suite}.sh" ;; *) echo "unknown suite: $suite" >&2; exit 64;; esac ;;
  evidence) "$ROOT/scripts/certification/collect_evidence.sh" ;;
  down) "$ROOT/scripts/certification/teardown.sh" ;;
  *) echo "usage: $0 {config|up [profile]|seed|test {backend|browser|security}|evidence|down}" >&2; exit 64 ;;
esac
