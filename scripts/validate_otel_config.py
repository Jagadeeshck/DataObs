#!/usr/bin/env python3
"""Static linter for config/otel-collector-poc.yaml.

Checks the small set of mistakes that have actually broken the POC
collector container (exit code 1 at startup):

  * docker_stats.api_version must be a string, not a YAML float.
    (`api_version: 1.44` parses as 1.44 (float); the receiver
    only accepts strings and aborts with `cannot unmarshal !!float`.)
  * health_check / pprof / zpages extensions, if declared in
    `extensions:`, must also appear in `service.extensions:` or
    they're loaded but never started.
  * Every receiver / processor / exporter referenced from a pipeline
    in `service.pipelines.*` must exist in the corresponding
    top-level section.
  * The OTLP receiver must expose both gRPC :4317 and HTTP :4318
    on 0.0.0.0 — the POC pipeline emits over both.
  * The health_check extension, if used, must bind to 0.0.0.0 (not
    127.0.0.1) so the host port mapping in docker-compose.poc.yml
    can reach it.

Usage:
    python3 scripts/validate_otel_config.py [path/to/config.yaml]
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment requirement
    sys.stderr.write(
        "ERROR: PyYAML is required. Install with `pip install pyyaml`.\n"
    )
    sys.exit(2)


def _err(problems: list[str], msg: str) -> None:
    problems.append(msg)


def validate(path: Path) -> list[str]:
    cfg = yaml.safe_load(path.read_text())
    problems: list[str] = []

    receivers = cfg.get("receivers") or {}
    processors = cfg.get("processors") or {}
    exporters = cfg.get("exporters") or {}
    extensions = cfg.get("extensions") or {}
    service = cfg.get("service") or {}

    # ── docker_stats.api_version must be a YAML string ─────────────
    ds = receivers.get("docker_stats")
    if ds is not None:
        api = ds.get("api_version")
        if api is not None and not isinstance(api, str):
            _err(
                problems,
                f"receivers.docker_stats.api_version must be a quoted "
                f"string, got {type(api).__name__} ({api!r}). Quote it as "
                f'`api_version: "{api}"` or remove the field to accept '
                f"the receiver's default.",
            )

    # ── OTLP receiver must expose both gRPC and HTTP on 0.0.0.0 ────
    otlp = receivers.get("otlp")
    if otlp is None:
        _err(problems, "receivers.otlp must be defined for the POC pipeline.")
    else:
        protos = (otlp.get("protocols") or {})
        for proto, expected_port in (("grpc", 4317), ("http", 4318)):
            p = protos.get(proto)
            if p is None:
                _err(
                    problems,
                    f"receivers.otlp.protocols.{proto} is missing; the "
                    f"POC pipeline emits OTLP over both gRPC and HTTP.",
                )
                continue
            ep = (p or {}).get("endpoint", "")
            if not ep.startswith("0.0.0.0:"):
                _err(
                    problems,
                    f"receivers.otlp.protocols.{proto}.endpoint must bind "
                    f"to 0.0.0.0, not {ep!r}, so the host port mapping "
                    f"works.",
                )
            elif not ep.endswith(f":{expected_port}"):
                _err(
                    problems,
                    f"receivers.otlp.protocols.{proto}.endpoint should end "
                    f":{expected_port} (got {ep!r}); the POC compose "
                    f"publishes that port.",
                )

    # ── health_check extension must bind to 0.0.0.0:13133 ──────────
    hc = extensions.get("health_check")
    if hc is not None:
        ep = (hc or {}).get("endpoint", "")
        if not ep.startswith("0.0.0.0:13133"):
            _err(
                problems,
                f"extensions.health_check.endpoint must be 0.0.0.0:13133 "
                f"(got {ep!r}); the docker-compose health probe and the "
                f"`make verify` script reach the collector on that port.",
            )

    # ── Every declared extension must be referenced by service ────
    declared_exts = set(extensions.keys())
    used_exts = set(service.get("extensions") or [])
    unused = declared_exts - used_exts
    if unused:
        _err(
            problems,
            f"extensions {sorted(unused)} are declared but not referenced "
            f"in service.extensions; they will not be started.",
        )

    # ── Every pipeline component must exist in its top-level map ──
    pipelines = (service.get("pipelines") or {})
    for pname, pipe in pipelines.items():
        for kind, table in (
            ("receivers", receivers),
            ("processors", processors),
            ("exporters", exporters),
        ):
            for ref in (pipe or {}).get(kind, []) or []:
                if ref not in table:
                    _err(
                        problems,
                        f"service.pipelines.{pname}.{kind}: '{ref}' is "
                        f"not defined in top-level {kind}.",
                    )

    return problems


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent.parent
    default = here / "config" / "otel-collector-poc.yaml"
    path = Path(argv[1]) if len(argv) > 1 else default
    if not path.exists():
        sys.stderr.write(f"ERROR: {path} not found\n")
        return 2
    problems = validate(path)
    if problems:
        print(f"FAIL: {path} has {len(problems)} issue(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK: {path} passes static lint.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
