from services.incident_manager.elasticsearch_repository import INCIDENTS_READ_ALIAS
from services.incident_manager.intelligence.elasticsearch_repository import ElasticsearchCandidateRepository
from services.incident_manager.intelligence.features import IncidentFeatures, _values
from services.incident_manager.intelligence.fingerprint import incident_fingerprint


def test_null_feature_is_unavailable():
    assert _values([None, "", "  "]) == ()


def test_fingerprint_independent_of_collection_order_and_deduplicates_set_like_features():
    base = dict(tenant_id="t", environment="prod", incident_id="i")
    assert incident_fingerprint(IncidentFeatures(**base, affected_assets=("b", "a"))) == incident_fingerprint(
        IncidentFeatures(**base, affected_assets=("a", "a", "b"))
    )


def test_similarity_repository_uses_canonical_incident_read_alias_and_requests_revision():
    class Client:
        def search(self, **kwargs):
            self.kwargs = kwargs
            return {"hits": {"hits": [{"_source": {"id": "i"}, "_seq_no": 7, "_primary_term": 2}]}}

    client = Client()
    source = IncidentFeatures(tenant_id="t", environment="prod", incident_id="s", affected_assets=("a",))
    result = ElasticsearchCandidateRepository(client).find_candidates(
        source, opened_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc), lookback_days=30
    )
    assert client.kwargs["index"] == INCIDENTS_READ_ALIAS
    assert client.kwargs["seq_no_primary_term"] is True
    assert result[0]["seq_no"] == 7 and result[0]["primary_term"] == 2
