"""Team 1 bounded resolver over the public Data Product read boundary."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from packages.pathways.product_impact import CanonicalMessagingResource

DEFAULT_DEPTH, MAX_DEPTH = 5, 8
DEFAULT_PRODUCTS, MAX_PRODUCTS = 50, 200
DEFAULT_EDGES, MAX_EDGES = 500, 1000
MAX_CONSUMERS = 500


class DataProductReadPort(Protocol):
    """No Team 2 persistence details cross this interface."""

    def get_product(self, tenant_id: str, environment: str, product_id: str) -> Any | None: ...
    def list_memberships(
        self, tenant_id: str, environment: str, *, entity_ids: Sequence[str], limit: int
    ) -> Sequence[Any]: ...
    def list_outputs(
        self, tenant_id: str, environment: str, *, entity_ids: Sequence[str], limit: int
    ) -> Sequence[Any]: ...
    def traverse_dependencies(
        self,
        tenant_id: str,
        environment: str,
        product_ids: Sequence[str],
        *,
        depth: int,
        product_limit: int,
        edge_limit: int,
    ) -> Any: ...
    def get_slo_summary(self, tenant_id: str, environment: str, product_id: str) -> Any: ...
    def list_known_consumers(
        self, tenant_id: str, environment: str, product_id: str, *, limit: int
    ) -> Sequence[Any]: ...


class ProductServiceUnavailable(RuntimeError):
    pass


class StreamProductImpactResolver:
    def __init__(self, port: DataProductReadPort) -> None:
        self.port = port

    @staticmethod
    def bounds(
        *, depth: int = DEFAULT_DEPTH, limit: int = DEFAULT_PRODUCTS, edge_limit: int = DEFAULT_EDGES
    ) -> tuple[int, int, int]:
        if not 0 <= depth <= MAX_DEPTH or not 1 <= limit <= MAX_PRODUCTS or not 1 <= edge_limit <= MAX_EDGES:
            raise ValueError("product impact query outside hard bounds")
        return depth, limit, edge_limit

    def resolve_resource_products(
        self, tenant_id: str, environment: str, resource: CanonicalMessagingResource, *, limit: int = DEFAULT_PRODUCTS
    ) -> list[Any]:
        self.bounds(limit=limit)
        keys = tuple(dict.fromkeys(filter(None, (resource.canonical_resource_id, resource.provider_resource_id))))
        try:
            memberships = self.port.list_memberships(tenant_id, environment, entity_ids=keys, limit=limit)
            outputs = self.port.list_outputs(tenant_id, environment, entity_ids=keys, limit=limit)
        except (TimeoutError, ConnectionError) as exc:
            raise ProductServiceUnavailable("product_service_unavailable") from exc
        # Strongest evidence wins, deterministically. The adapter remains responsible for scope filtering.
        ranked: dict[str, Any] = {}
        for item in sorted((*outputs, *memberships), key=lambda value: str(getattr(value, "product_id", ""))):
            if (
                getattr(item, "tenant_id", tenant_id) != tenant_id
                or getattr(item, "environment", environment) != environment
            ):
                continue
            product_id = str(getattr(item, "product_id"))
            candidate_rank = 0 if getattr(item, "state", None) == "active" else 1
            if product_id not in ranked or candidate_rank == 0:
                ranked[product_id] = item
        return [ranked[key] for key in sorted(ranked)][:limit]

    def resolve_downstream_products(
        self,
        tenant_id: str,
        environment: str,
        product_ids: Sequence[str],
        *,
        depth: int = DEFAULT_DEPTH,
        limit: int = DEFAULT_PRODUCTS,
        edge_limit: int = DEFAULT_EDGES,
    ) -> Any:
        depth, limit, edge_limit = self.bounds(depth=depth, limit=limit, edge_limit=edge_limit)
        return self.port.traverse_dependencies(
            tenant_id,
            environment,
            tuple(sorted(set(product_ids))),
            depth=depth,
            product_limit=limit,
            edge_limit=edge_limit,
        )

    def resolve_product_context(
        self, tenant_id: str, environment: str, product_id: str, *, include_slos: bool = True
    ) -> tuple[Any | None, Any | None]:
        product = self.port.get_product(tenant_id, environment, product_id)
        return product, (
            self.port.get_slo_summary(tenant_id, environment, product_id) if product and include_slos else None
        )

    def resolve_known_consumers(
        self, tenant_id: str, environment: str, product_id: str, *, limit: int = 100
    ) -> Sequence[Any]:
        if not 1 <= limit <= MAX_CONSUMERS:
            raise ValueError("consumer limit outside hard bounds")
        return self.port.list_known_consumers(tenant_id, environment, product_id, limit=limit)

    def resolve_pathway_products(
        self,
        tenant_id: str,
        environment: str,
        resources: Sequence[CanonicalMessagingResource],
        *,
        limit: int = DEFAULT_PRODUCTS,
    ) -> list[Any]:
        self.bounds(limit=limit)
        products: dict[str, Any] = {}
        for resource in resources[:MAX_PRODUCTS]:
            for binding in self.resolve_resource_products(tenant_id, environment, resource, limit=limit):
                products.setdefault(str(getattr(binding, "product_id")), binding)
                if len(products) >= limit:
                    return [products[key] for key in sorted(products)]
        return [products[key] for key in sorted(products)]

    def resolve_application_products(
        self, tenant_id: str, environment: str, application_id: str, *, limit: int = DEFAULT_PRODUCTS
    ) -> list[Any]:
        resource = CanonicalMessagingResource(
            messaging_system="otel", resource_kind="application", canonical_resource_id=application_id
        )
        return self.resolve_resource_products(tenant_id, environment, resource, limit=limit)
