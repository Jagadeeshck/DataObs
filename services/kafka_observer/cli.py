from __future__ import annotations

import argparse
import json

from .collector_registry import CAPABILITIES


def main() -> int:
    parser = argparse.ArgumentParser(prog="dataobs-kafka-observer")
    parser.add_argument(
        "command", choices=["run", "test-connection", "inventory", "collect-once", "print-capabilities"]
    )
    args = parser.parse_args()
    if args.command == "print-capabilities":
        print(json.dumps(sorted(CAPABILITIES)))
    else:
        parser.error("configure the observer through config/kafka-observer.example.yaml before collection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
