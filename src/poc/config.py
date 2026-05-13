"""
POC configuration loader.

Supports both legacy ``config/dataobs.yaml`` files with a top-level ``poc:``
section and the current standalone ``config/dataobs_poc.yaml`` file used by
Docker Compose. Environment placeholders in the form ``${VAR}`` or
``${VAR:-default}`` are expanded before YAML parsing.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict

import yaml

_DEFAULT_CONFIG_CANDIDATES = (
    "config/dataobs.yaml",
    "config/dataobs_poc.yaml",
    "config/dataobs.example.yaml",
)
_ENV_PATTERN = re.compile(r"\$\{([^}:]+)(?::-([^}]*))?\}")


def _env_or_none(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _expand_env_placeholders(value: str) -> str:
    """Expand shell-style environment placeholders in a config string."""

    def replace(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        return os.environ.get(name, default or "")

    return _ENV_PATTERN.sub(replace, value)


def _candidate_paths(path: str | None = None) -> list[str]:
    if path:
        return [path]
    env_path = _env_or_none("DATAOBS_CONFIG", "DATAOBS_POC_CONFIG")
    if env_path:
        return [env_path, *_DEFAULT_CONFIG_CANDIDATES]
    return list(_DEFAULT_CONFIG_CANDIDATES)


def load_config(path: str | None = None) -> Dict[str, Any]:
    """Load the first available DataObs configuration file."""
    for candidate in _candidate_paths(path):
        if os.path.exists(candidate):
            raw = Path(candidate).read_text(encoding="utf-8")
            return yaml.safe_load(_expand_env_placeholders(raw)) or {}
    return {}


def _is_standalone_poc_config(cfg: Dict[str, Any]) -> bool:
    """Return True for the dedicated config/dataobs_poc.yaml shape."""
    pipeline = cfg.get("pipeline") or {}
    runner = str(pipeline.get("runner", ""))
    return (
        cfg.get("tenant") == "poc"
        or cfg.get("environment") == "poc"
        or "src.poc" in runner
        or "dataobs-poc" in str(cfg.get("otel", {})).lower()
    )


def get_poc_config(path: str | None = None) -> Dict[str, Any]:
    """
    Return normalized POC settings.

    Legacy configs store settings under ``poc``. The POC Docker stack uses a
    standalone file (``config/dataobs_poc.yaml``), so when no nested section is
    present and the document is explicitly POC-shaped we return the whole
    document with ``enabled`` defaulting to ``True``.
    """
    cfg = load_config(path)
    if not cfg:
        return {}

    if isinstance(cfg.get("poc"), dict):
        poc_cfg = dict(cfg["poc"])
    elif _is_standalone_poc_config(cfg):
        poc_cfg = dict(cfg)
        poc_cfg.setdefault("enabled", True)
    else:
        poc_cfg = {}

    poc_cfg.setdefault("runtime", {})
    poc_cfg["runtime"].setdefault("checkpoint_dir", "/tmp/dataobs/checkpoints")
    poc_cfg["runtime"].setdefault("raw_download_dir", "/tmp/dataobs/raw")
    poc_cfg["runtime"].setdefault("curated_output_dir", "/tmp/dataobs/curated")
    poc_cfg["runtime"].setdefault("temp_dir", "/tmp/dataobs/tmp")
    return poc_cfg


def ensure_dirs(poc_cfg: Dict[str, Any]) -> None:
    """Create all runtime working directories declared in config."""
    runtime = poc_cfg.get("runtime", {})
    for key in ["checkpoint_dir", "raw_download_dir", "curated_output_dir", "temp_dir"]:
        val = runtime.get(key)
        if val:
            Path(val).mkdir(parents=True, exist_ok=True)
