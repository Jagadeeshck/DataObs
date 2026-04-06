from src.analytics.elasticsearch_ml import ElasticsearchMLManager, MLJobConfig


class _MLApi:
    def __init__(self):
        self.calls = []

    def put_job(self, job_id, body):
        self.calls.append(("put_job", job_id, body))

    def put_datafeed(self, datafeed_id, body):
        self.calls.append(("put_datafeed", datafeed_id, body))

    def open_job(self, job_id):
        self.calls.append(("open_job", job_id))

    def start_datafeed(self, datafeed_id, start):
        self.calls.append(("start_datafeed", datafeed_id, start))
        return {"started": True}


class _FakeES:
    def __init__(self):
        self.ml = _MLApi()
        self.search_calls = []

    def search(self, index, body):
        self.search_calls.append((index, body))
        return {"hits": {"hits": []}}


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


def test_get_top_anomalies_uses_ml_index():
    es = _FakeES()
    manager = ElasticsearchMLManager(es)

    manager.get_top_anomalies(job_id="dataobs-freshness-age-anomaly", severity_threshold=70, size=5)

    assert es.search_calls[0][0] == ".ml-anomalies-*"
    query = es.search_calls[0][1]["query"]["bool"]["filter"]
    assert {"range": {"record_score": {"gte": 70}}} in query
