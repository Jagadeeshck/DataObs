"""Lease semantics are implemented by :mod:`services.job_reliability.repository`."""

from .repository import ConflictError

__all__ = ["ConflictError"]
