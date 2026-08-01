from services.product_query.stream_repository import StreamRepository


class FakeElasticsearch:
    def __init__(self):
        self.request = None

    def search(self, **request):
        self.request = request
        return {"hits": {"hits": []}}


def test_stream_filters_are_server_side_bounded_and_do_not_use_wildcards():
    es = FakeElasticsearch()
    StreamRepository(es).search(
        "streams",
        "tenant-a",
        "prod",
        size=51,
        search="orders*?",
        health="critical",
        retention_risk="at_risk",
        cluster_id="cluster-a",
        consumer_group_id="group-a",
        has_lag=True,
        sort="maximum_lag",
    )
    request = es.request
    assert request["size"] == 51
    filters = request["query"]["bool"]["filter"]
    assert {"term": {"tenant_id": "tenant-a"}} in filters
    assert {"term": {"environment": "prod"}} in filters
    assert {"range": {"maximum_lag": {"gt": 0}}} in filters
    assert request["query"]["bool"]["must"][0]["multi_match"]["query"] == "orders*?"
    assert "wildcard" not in repr(request["query"])
    assert request["sort"][0]["maximum_lag"]["order"] == "desc"


def test_stream_search_after_is_forwarded_without_offset_pagination():
    es = FakeElasticsearch()
    StreamRepository(es).search("streams", "tenant-a", "prod", search_after=[3, "id"], sort="health")
    assert es.request["search_after"] == [3, "id"]
    assert "from_" not in es.request and "from" not in es.request
