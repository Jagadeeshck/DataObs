from __future__ import annotations

import hashlib
import json

from .features import FEATURE_VERSION, FailureSignature, IncidentFeatures

FINGERPRINT_VERSION = "incident-fingerprint/v1"
FAILURE_SIGNATURE_VERSION = "failure-signature/v1"


def _digest(version: str, payload: dict[str, object]) -> str:
    canonical = json.dumps({"version": version, **payload}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def failure_signature_fingerprint(signature: FailureSignature) -> str:
    return f"{FAILURE_SIGNATURE_VERSION}:{_digest(FAILURE_SIGNATURE_VERSION, signature.model_dump(mode='json'))}"


def incident_fingerprint(features: IncidentFeatures) -> str:
    # Scope and record identity are intentionally excluded: this is a structural signature,
    # never proof of a shared root cause.
    excluded = {"tenant_id", "environment", "incident_id", "source_revision", "merged_from", "split_from"}
    payload = features.model_dump(mode="json", exclude=excluded)
    payload["feature_version"] = FEATURE_VERSION
    return f"{FINGERPRINT_VERSION}:{_digest(FINGERPRINT_VERSION, payload)}"
