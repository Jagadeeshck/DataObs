from services.pathway_worker.repository import ElasticsearchPathwayRepository


class FakeES:
    def __init__(self):
        self.calls = 0
        self.closed = 0

    def open_point_in_time(self, **kwargs):
        return {"id": "pit-1"}

    def search(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return {
                "hits": {
                    "hits": [
                        {"_id": "a", "_source": {"tenant_id": "a"}, "sort": [1, 1]},
                        {"_id": "b", "_source": {"tenant_id": "a"}, "sort": [2, 2]},
                    ]
                }
            }
        return {"hits": {"hits": [{"_id": "c", "_source": {"tenant_id": "a"}, "sort": [3, 3]}]}}

    def close_point_in_time(self, **kwargs):
        self.closed += 1


def test_multipage_window_retains_one_pit_and_does_not_export_pit_cursor():
    es = FakeES()
    repo = ElasticsearchPathwayRepository(es, "a", "prod", ["traces-apm-*"])
    docs, cursor = repo.read_spans(after=None, since="2026-01-01T00:00:00Z", size=2)
    assert [doc["_source_document_id"] for doc in docs] == ["a", "b"]
    assert cursor == [2, 2]
    assert es.calls == 1 and es.closed == 1
