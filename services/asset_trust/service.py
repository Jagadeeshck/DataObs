"""Application orchestration for one deterministic Asset Trust evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

from .scoring import calculate_asset_trust


class AssetTrustService:
    def __init__(self, repository, evidence_resolver):
        self.repository = repository
        self.evidence_resolver = evidence_resolver

    def evaluate(self, tenant_id, environment, asset_id, policy, *, window_start, window_end, calculated_at=None):
        evidence = self.evidence_resolver.resolve(tenant_id, environment, asset_id, now=calculated_at)
        score = calculate_asset_trust(
            tenant_id=tenant_id,
            environment=environment,
            asset_id=asset_id,
            evidence=evidence,
            policy=policy,
            window_start=window_start,
            window_end=window_end,
            calculated_at=calculated_at or datetime.now(timezone.utc),
        )
        self.repository.append_score(score)
        return score

    @staticmethod
    def recommendations(score):
        actions = {
            "contract_compliance": "define Data Contract",
            "observability_coverage": "add monitor coverage",
            "lineage_and_governance": "assign owner and improve lineage coverage",
            "delivery_reliability": "investigate unreliable producer job",
            "slo_reliability": "investigate exhausted SLO",
        }
        return [
            {"dimension": d.name, "action": actions[d.name], "auto_apply": False}
            for d in score.dimensions
            if d.name in actions and (d.score is None or d.score < 65)
        ]
