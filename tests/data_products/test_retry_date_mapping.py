from datetime import datetime, timezone

from packages.elastic_store.manifest import (
    DATA_PRODUCT_RECONCILIATION_RETRY_DATE_MIGRATION,
    migrations,
)
from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository


class SearchClient:
    def __init__(self):
        self.request = None

    def search(self, **request):
        self.request = request
        return {"hits": {"hits": []}}


def test_0017_adds_only_the_mapped_retry_date():
    migration = DATA_PRODUCT_RECONCILIATION_RETRY_DATE_MIGRATION
    assert migrations()[-1] is migration
    assert migration.dependencies == ["0016_data_product_membership_dependency_runtime"]
    assert migration.operations == {
        "mapping_updates": {"dataobs-data-product-operation-state-v1": {"next_attempt_at": {"type": "date"}}}
    }


def test_retry_query_uses_top_level_date_and_one_concrete_utc_instant():
    client = SearchClient()
    ElasticsearchDataProductRepository(client).list_reconcilable_operations("tenant", "prod")
    filters = client.request["query"]["bool"]["filter"]
    rendered = str(filters)
    assert "document.next_attempt_at" not in rendered
    assert "'next_attempt_at'" in rendered
    assert "'now'" not in rendered
    instants = []
    for item in filters:
        for clause in item.get("bool", {}).get("should", []):
            for value in clause.get("range", {}).values():
                instants.append(value["lte"])
    assert len(instants) == 2 and instants[0] == instants[1]
    assert datetime.fromisoformat(instants[0]).tzinfo == timezone.utc
