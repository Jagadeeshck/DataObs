"""
Tests for ElasticsearchMLManager.

Uses fake ML/ES clients — no real Elasticsearch needed.
The mocks accept the elasticsearch-py 8.x keyword-argument API
(body= is removed; all params passed as keyword args).
"""

from src.analytics.elasticsearch_ml import ElasticsearchMLManager, MLJobConfig

# ---------------------------------------------------------------------------
# Fake ML sub-client (mirrors es.ml.*)
# ---------------------------------------------------------------------------


class _MLApi:
    def __init__(self):
        self.calls: list = []

    def put_job(self, job_id, **kwargs):  # was: put_job(self, job_id, body)
        self.calls.append(("put_job", job_id, kwargs))

    def put_datafeed(self, datafeed_id, **kwargs):  # was: put_datafeed(self, datafeed_id, body)
        self.calls.append(("put_datafeed", datafeed_id, kwargs))

    def open_job(self, job_id):
        self.calls.append(("open_job", job_id))

    def start_datafeed(self, datafeed_id, start):
        self.calls.append(("start_datafeed", datafeed_id, start))
        return {"started": True}


# ---------------------------------------------------------------------------
# Fake ES client (mirrors es.search with keyword-arg API)
# ---------------------------------------------------------------------------


class _FakeES:
    def __init__(self):
        self.ml = _MLApi()
        self.search_calls: list = []

    def search(self, index, **kwargs):  # was: search(self, index, body)
        self.search_calls.append({"index": index, **kwargs})
        return {"hits": {"hits": []}}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ensure_job_creates_job_and_datafeed():
    es = _FakeES()
    manager = ElasticsearchMLManager(es)

    manager.ensure_job(
        MLJobConfig(
            job_id="dataobs-freshness-age-anomaly",
            description="freshness",
            index_pattern="dataobs-freshness*",
        )
    )

    call_names = [c[0] for c in es.ml.calls]
    assert "put_job" in call_names
    assert "put_datafeed" in call_names


def test_ensure_job_passes_correct_job_id():
    es = _FakeES()
    manager = ElasticsearchMLManager(es)

    manager.ensure_job(
        MLJobConfig(
            job_id="my-custom-job",
            description="test",
            index_pattern="dataobs-*",
        )
    )

    put_job_calls = [(c[1]) for c in es.ml.calls if c[0] == "put_job"]
    assert "my-custom-job" in put_job_calls


def test_get_top_anomalies_searches_ml_index():
    es = _FakeES()
    manager = ElasticsearchMLManager(es)

    manager.get_top_anomalies(job_id="dataobs-freshness-age-anomaly", severity_threshold=70, size=5)

    assert len(es.search_calls) == 1
    call = es.search_calls[0]
    assert call["index"] == ".ml-anomalies-*"
    assert call["size"] == 5


def test_get_top_anomalies_applies_severity_filter():
    es = _FakeES()
    manager = ElasticsearchMLManager(es)

    manager.get_top_anomalies(job_id="dataobs-freshness-age-anomaly", severity_threshold=70, size=5)

    query_filters = es.search_calls[0]["query"]["bool"]["filter"]
    range_filters = [f for f in query_filters if "range" in f]
    assert any(f["range"].get("record_score", {}).get("gte") == 70 for f in range_filters)


def test_get_top_anomalies_applies_job_id_filter():
    es = _FakeES()
    manager = ElasticsearchMLManager(es)

    manager.get_top_anomalies(job_id="dataobs-freshness-age-anomaly", severity_threshold=50)

    query_filters = es.search_calls[0]["query"]["bool"]["filter"]
    term_filters = [f for f in query_filters if "term" in f]
    assert any(f["term"].get("job_id") == "dataobs-freshness-age-anomaly" for f in term_filters)
