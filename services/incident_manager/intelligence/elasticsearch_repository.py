from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .features import IncidentFeatures
from .repository import ALLOWED_LOOKBACK_DAYS, MAX_CANDIDATE_POOL

INCIDENT_READ_ALIAS = "dataobs-incidents-read"


class ElasticsearchCandidateRepository:
    """Bounded candidate generation; scoring remains deterministic in application code."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def find_candidates(
        self, source: IncidentFeatures, *, opened_at: datetime, lookback_days: int, limit: int = MAX_CANDIDATE_POOL
    ) -> list[dict[str, Any]]:
        if lookback_days not in ALLOWED_LOOKBACK_DAYS:
            raise ValueError("lookback must be one of 30, 90, 180, or 365 days")
        should = []
        for field, values in (
            ("affected_assets", source.affected_assets),
            ("data_product_ids", source.data_product_ids),
            ("business_services", source.business_services),
            ("correlation_key", source.correlation_keys),
        ):
            if values:
                should.append({"terms": {field: list(values)}})
        if not should:
            return []
        response = self.client.search(
            index=INCIDENT_READ_ALIAS,
            size=min(max(1, limit), MAX_CANDIDATE_POOL),
            timeout="2s",
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": source.tenant_id}},
                        {"term": {"environment": source.environment}},
                        {
                            "range": {
                                "opened_at": {
                                    "gte": (opened_at - timedelta(days=lookback_days))
                                    .astimezone(timezone.utc)
                                    .isoformat(),
                                    "lt": opened_at.isoformat(),
                                }
                            }
                        },
                    ],
                    "must_not": [{"term": {"id": source.incident_id}}],
                    "should": should,
                    "minimum_should_match": 1,
                }
            },
            sort=[{"opened_at": "desc"}, {"id": "asc"}],
        )
        return [hit["_source"] for hit in response["hits"]["hits"]]
