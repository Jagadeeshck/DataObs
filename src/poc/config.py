"""
POC configuration loader.

Reads ``config/dataobs.yaml`` (falls back to ``config/dataobs.example.yaml``)
and returns the ``poc:`` block as a plain dict.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(path: str = "config/dataobs.yaml") -> Dict[str, Any]:
    candidates = [path, "config/dataobs.example.yaml"]
    for candidate in candidates:
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
    return {}


def get_poc_config(path: str = "config/dataobs.yaml") -> Dict[str, Any]:
    """Return the ``poc:`` section from the DataObs config."""
    cfg = load_config(path)
    return cfg.get("poc", {})


def ensure_dirs(poc_cfg: Dict[str, Any]) -> None:
    """Create all runtime working directories declared in config."""
    runtime = poc_cfg.get("runtime", {})
    for key in ["checkpoint_dir", "raw_download_dir", "curated_output_dir", "temp_dir"]:
        val = runtime.get(key)
        if val:
            Path(val).mkdir(parents=True, exist_ok=True)
