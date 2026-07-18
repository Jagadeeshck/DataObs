from __future__ import annotations

from packages.domain_model.incident import Finding, deterministic_id


def correlation_key(finding: Finding) -> str:
    return deterministic_id(
        "corr",
        [
            finding.tenant_id,
            finding.environment,
            finding.source_id or "source",
            finding.asset_id,
            finding.correlation_id or "none",
        ],
    )
