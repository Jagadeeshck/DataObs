"""Bounded Elasticsearch projection provider; never reads payload bodies."""

from __future__ import annotations

from services.monitoring.providers.base import CapabilityState, ProviderBudget, ProviderResult


class ProjectionProvider:
    def __init__(self, client, *, index: str, value_field: str):
        self.client = client
        self.index = index
        self.value_field = value_field

    def validate(self, target, budget):
        return CapabilityState.SUPPORTED if target else CapabilityState.NOT_CONFIGURED

    def observe(self, tenant_id, environment, target, budget: ProviderBudget):
        query = {
            "bool": {
                "filter": [
                    {"term": {"tenant_id": tenant_id}},
                    {"term": {"environment": environment}},
                    {"range": {"@timestamp": {"gte": target.get("start"), "lt": target.get("end")}}},
                ]
            }
        }
        response = self.client.search(
            index=self.index,
            query=query,
            size=min(budget.maximum_result_size, 100),
            _source=[self.value_field, "@timestamp"],
        )
        hits = response["hits"]["hits"]
        values = [h["_source"].get(self.value_field) for h in hits if h["_source"].get(self.value_field) is not None]
        return ProviderResult(
            CapabilityState.SUPPORTED,
            value=float(values[-1]) if values else None,
            sample_count=len(values),
            source_coverage=1 if values else 0,
            confidence=1 if values else 0,
            missing_data=not values,
            evidence_refs=tuple(str(h.get("_id")) for h in hits[:10]),
        )
