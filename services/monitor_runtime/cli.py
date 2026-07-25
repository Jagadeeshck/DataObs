from __future__ import annotations

import argparse
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run", "once", "health", "reconcile-definitions"])
    args = parser.parse_args()
    # Composition is deliberately environment-owned; health remains usable in image probes.
    if args.command == "health":
        print(
            json.dumps(
                {"service": "monitor-runtime", "live": True, "ready": False, "reason": "repository_not_composed"}
            )
        )
        return
    raise SystemExit("compose MonitorRuntime with configured Elasticsearch and provider registry")


if __name__ == "__main__":
    main()
