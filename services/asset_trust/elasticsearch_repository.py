"""Elasticsearch 9 asset trust repository with scoped IDs, filters, and OCC."""

from hashlib import sha256

from elasticsearch import ConflictError, NotFoundError

from packages.domain_model.asset_trust import AssetTrustPolicy, AssetTrustScore

from .repository import PolicyConflict

POLICIES = "dataobs-asset-trust-policy-v1"
CURRENT = "dataobs-asset-trust-current-v1"
HISTORY = "logs-dataobs.asset-trust-evaluation-default"


def scoped_id(tenant, environment, value):
    return sha256(f"{tenant}\0{environment}\0{value}".encode()).hexdigest()


class ElasticsearchAssetTrustRepository:
    def __init__(self, client):
        self.client = client

    def create_policy(self, tenant_id, environment, policy):
        try:
            self.client.create(
                index=POLICIES,
                id=scoped_id(tenant_id, environment, policy.policy_id),
                document=policy.model_dump(mode="json") | {"tenant_id": tenant_id, "environment": environment},
            )
        except ConflictError as exc:
            raise PolicyConflict("policy already exists") from exc

    def get_policy(self, tenant_id, environment, policy_id):
        try:
            hit = self.client.get(index=POLICIES, id=scoped_id(tenant_id, environment, policy_id))
        except NotFoundError:
            return None
        source = hit["_source"]
        if source.get("tenant_id") != tenant_id or source.get("environment") != environment:
            return None
        return AssetTrustPolicy.model_validate(
            {k: v for k, v in source.items() if k not in ("tenant_id", "environment")}
        )

    def list_policies(self, tenant_id, environment, *, limit, after=None):
        query = {"bool": {"filter": [{"term": {"tenant_id": tenant_id}}, {"term": {"environment": environment}}]}}
        result = self.client.search(index=POLICIES, size=min(limit, 200), query=query, sort=[{"policy_id": "asc"}])
        return [
            AssetTrustPolicy.model_validate(
                {k: v for k, v in h["_source"].items() if k not in ("tenant_id", "environment")}
            )
            for h in result["hits"]["hits"]
        ]

    def update_policy(self, tenant_id, environment, policy, *, expected_etag):
        doc_id = scoped_id(tenant_id, environment, policy.policy_id)
        hit = self.client.get(index=POLICIES, id=doc_id)
        if hit["_source"].get("etag") != expected_etag:
            raise PolicyConflict("stale ETag")
        try:
            self.client.index(
                index=POLICIES,
                id=doc_id,
                document=policy.model_dump(mode="json") | {"tenant_id": tenant_id, "environment": environment},
                if_seq_no=hit["_seq_no"],
                if_primary_term=hit["_primary_term"],
            )
        except ConflictError as exc:
            raise PolicyConflict("stale ETag") from exc

    def append_score(self, score):
        doc = score.model_dump(mode="json")
        try:
            self.client.create(
                index=HISTORY, id=scoped_id(score.tenant_id, score.environment, score.score_id), document=doc
            )
        except ConflictError:
            return False
        self.client.index(index=CURRENT, id=scoped_id(score.tenant_id, score.environment, score.asset_id), document=doc)
        return True

    def get_current_score(self, tenant_id, environment, asset_id):
        try:
            hit = self.client.get(index=CURRENT, id=scoped_id(tenant_id, environment, asset_id))
        except NotFoundError:
            return None
        s = hit["_source"]
        return (
            AssetTrustScore.model_validate(s)
            if (s.get("tenant_id"), s.get("environment")) == (tenant_id, environment)
            else None
        )

    def _search(self, index, tenant, environment, limit, extra=None, sort=None):
        filters = [{"term": {"tenant_id": tenant}}, {"term": {"environment": environment}}] + (extra or [])
        return self.client.search(
            index=index,
            size=min(limit, 200),
            query={"bool": {"filter": filters}},
            sort=sort or [{"calculated_at": "desc"}],
        )["hits"]["hits"]

    def list_score_history(self, tenant_id, environment, asset_id, *, limit, after=None):
        return [
            AssetTrustScore.model_validate(h["_source"])
            for h in self._search(HISTORY, tenant_id, environment, limit, [{"term": {"asset_id": asset_id}}])
        ]

    def list_assets_by_score(self, tenant_id, environment, *, limit, maximum_score=None):
        extra = [] if maximum_score is None else [{"range": {"score": {"lte": maximum_score}}}]
        return [
            AssetTrustScore.model_validate(h["_source"])
            for h in self._search(
                CURRENT, tenant_id, environment, limit, extra, [{"score": "asc"}, {"asset_id": "asc"}]
            )
        ]

    def bulk_get_scores(self, tenant_id, environment, asset_ids):
        return {a: self.get_current_score(tenant_id, environment, a) for a in asset_ids[:500]}

    def runtime_health(self, tenant_id, environment):
        return {
            "status": "healthy",
            "current_scores": self.client.count(
                index=CURRENT,
                query={
                    "bool": {"filter": [{"term": {"tenant_id": tenant_id}}, {"term": {"environment": environment}}]}
                },
            )["count"],
        }
