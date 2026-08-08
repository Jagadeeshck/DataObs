"""Metadata-only failure candidate classification facade."""

from packages.streaming.intelligence import classify_failure_candidate, safe_error_fingerprint

__all__ = ["classify_failure_candidate", "safe_error_fingerprint"]
