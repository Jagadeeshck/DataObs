"""Deterministic, metadata-only DataObs platform lifecycle control plane."""

from .service import LifecycleError, PlatformLifecycleService

__all__ = ["LifecycleError", "PlatformLifecycleService"]
