"""Production Data Product persistence with fixed resources and Elasticsearch OCC."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from elasticsearch import ConflictError, Elasticsearch, NotFoundError

from packages.domain_model.data_product import DataProduct, DataProductRevisionEvent
from services.data_products.events import ProductConsistencyError
from services.data_products.repository import ProductVersionConflict

PRODUCTS = "dataobs-data-products-v1"
REVISIONS = "dataobs-data-product-revisions-v1"
OPERATIONS = "dataobs-data-product-operation-state-v1"
REQUIRED_RESOURCES = (
    PRODUCTS,
    REVISIONS,
    "dataobs-data-product-membership-v1",
    "dataobs-data-product-slos-v1",
    "dataobs-data-product-scorecards-v1",
    "dataobs-data-product-membership-proposals-v1",
    "dataobs-data-product-membership-decisions-v1",
    "dataobs-data-product-dependency-current-v1",
    "dataobs-data-product-slo-evaluations-v1",
    "dataobs-data-product-coverage-v1",
    "dataobs-data-product-impact-current-v1",
    "dataobs-data-product-operation-state-v1",
    "dataobs-data-product-idempotency-v1",
)


def scoped_id(tenant_id: str, environment: str, entity_id: str) -> str:
    if not tenant_id or not environment:
        raise ValueError("tenant_id and environment are mandatory")
    return sha256(f"{tenant_id}\0{environment}\0{entity_id}".encode()).hexdigest()


class ElasticsearchDataProductRepository:
    def __init__(self, client: Elasticsearch) -> None:
        self.client = client

    def create_product(self, product: DataProduct) -> DataProduct:
        try:
            self.client.create(
                index=PRODUCTS,
                id=scoped_id(product.tenant_id, product.environment, product.id),
                document=product.model_dump(mode="json"),
            )
        except ConflictError as exc:
            raise ProductVersionConflict("data product exists") from exc
        return product

    def get_product(self, tenant_id: str, environment: str, product_id: str) -> DataProduct | None:
        try:
            hit = self.client.get(
                index=PRODUCTS, id=scoped_id(tenant_id, environment, product_id), seq_no_primary_term=True
            )
        except NotFoundError:
            return None
        source = hit["_source"]
        if (source.get("tenant_id"), source.get("environment")) != (tenant_id, environment):
            return None
        return DataProduct.model_validate(source)

    def list_products(
        self, tenant_id: str, environment: str, *, limit: int, cursor: str | None = None
    ) -> list[DataProduct]:
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        body: dict[str, Any] = {
            "index": PRODUCTS,
            "size": limit,
            "query": {"bool": {"filter": [{"term": {"tenant_id": tenant_id}}, {"term": {"environment": environment}}]}},
            "sort": [{"id": "asc"}, {"_id": "asc"}],
        }
        if cursor:
            body["search_after"] = [cursor, scoped_id(tenant_id, environment, cursor)]
        hits = self.client.search(**body)["hits"]["hits"]
        return [DataProduct.model_validate(hit["_source"]) for hit in hits]

    def update_product(self, product: DataProduct, *, expected_etag: str) -> DataProduct:
        document_id = scoped_id(product.tenant_id, product.environment, product.id)
        try:
            hit = self.client.get(index=PRODUCTS, id=document_id, seq_no_primary_term=True)
            if hit["_source"].get("etag") != expected_etag:
                raise ProductVersionConflict("stale data product ETag")
            if int(hit["_source"].get("revision", 0)) >= product.revision:
                raise ProductVersionConflict("stale data product revision")
            self.client.index(
                index=PRODUCTS,
                id=document_id,
                document=product.model_dump(mode="json"),
                if_seq_no=hit["_seq_no"],
                if_primary_term=hit["_primary_term"],
            )
        except ConflictError as exc:
            raise ProductVersionConflict("concurrent data product update") from exc
        return product

    def append_revision(self, product: DataProduct, *, actor: str, reason: str) -> None:
        event_id = scoped_id(product.tenant_id, product.environment, f"{product.id}:{product.revision}")
        document = {
            "tenant_id": product.tenant_id,
            "environment": product.environment,
            "product_id": product.id,
            "revision": product.revision,
            "etag": product.etag,
            "actor": actor,
            "reason": reason,
            "document": product.model_dump(mode="json"),
        }
        try:
            self.client.create(index=REVISIONS, id=event_id, document=document)
        except ConflictError as exc:
            existing = self.client.get(index=REVISIONS, id=event_id)["_source"]
            if existing == document:
                return
            raise ProductConsistencyError("divergent same-revision payload") from exc

    def begin_operation(self, event: DataProductRevisionEvent, product: DataProduct) -> DataProductRevisionEvent:
        document = event.model_dump(mode="json") | {"document": product.model_dump(mode="json")}
        try:
            self.client.create(index=OPERATIONS, id=event.operation_id, document=document)
            return event
        except ConflictError as exc:
            existing = self.client.get(index=OPERATIONS, id=event.operation_id)["_source"]
            if existing.get("definition_checksum") != event.definition_checksum:
                raise ProductConsistencyError("divergent operation replay") from exc
            return DataProductRevisionEvent.model_validate(
                {key: value for key, value in existing.items() if key != "document"}
            )

    def finish_operation(self, event: DataProductRevisionEvent) -> None:
        outcome_id = scoped_id(event.tenant_id, event.environment, f"{event.operation_id}:{event.outcome}")
        try:
            self.client.create(index=REVISIONS, id=outcome_id, document=event.model_dump(mode="json"))
        except ConflictError as exc:
            existing = self.client.get(index=REVISIONS, id=outcome_id)["_source"]
            if existing != event.model_dump(mode="json"):
                raise ProductConsistencyError("divergent operation outcome") from exc

    def readiness(self) -> dict[str, Any]:
        """Return diagnostic readiness; never collapse a partial migration to healthy."""
        resources: dict[str, dict[str, Any]] = {}
        reasons: list[dict[str, str]] = []
        for name in REQUIRED_RESOURCES:
            exists = bool(self.client.indices.exists(index=name))
            detail: dict[str, Any] = {"exists": exists, "alias_target_valid": False, "write_blocked": False}
            if not exists:
                reasons.append({"code": "resource_missing", "resource": name})
                resources[name] = detail
                continue
            aliases = self.client.indices.get_alias(index=name)
            concrete = next(iter(aliases))
            installed_aliases = aliases[concrete].get("aliases", {})
            write_alias = f"{name}-write"
            detail["alias_target_valid"] = bool(installed_aliases.get(write_alias, {}).get("is_write_index"))
            if not detail["alias_target_valid"]:
                reasons.append({"code": "write_alias_invalid", "resource": name})
            settings = self.client.indices.get_settings(index=name)[concrete].get("settings", {}).get("index", {})
            detail["write_blocked"] = str(settings.get("blocks", {}).get("write", "false")).lower() == "true"
            if detail["write_blocked"]:
                reasons.append({"code": "resource_write_blocked", "resource": name})
            mapping = self.client.indices.get_mapping(index=name)[concrete].get("mappings", {})
            detail["strict_mapping"] = mapping.get("dynamic") == "strict"
            if not detail["strict_mapping"]:
                reasons.append({"code": "strict_mapping_missing", "resource": name})
            resources[name] = detail
        return {"ready": not reasons, "resources": resources, "reasons": reasons}
