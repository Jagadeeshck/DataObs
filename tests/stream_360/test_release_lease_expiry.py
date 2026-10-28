"""An unchanged fencing token does not authorize an expired worker."""

from datetime import datetime, timedelta, timezone

import pytest

from services.kafka_observer.intelligence_repository import ElasticsearchIntelligenceRepository
from services.kafka_observer.reliability_repository import ElasticsearchReliabilityRepository
from services.kafka_observer.reliability_runtime import StaleWriter
from services.kafka_observer.schema_intelligence_repository import ElasticsearchSchemaIntelligenceRepository


class LeaseStore:
    def __init__(self, seconds, token=7):
        self.expiry = (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()
        self.token = token

    def get(self, **kwargs):
        return {
            "_source": {
                "fencing_token": self.token,
                "expires_at": self.expiry,
                "lease_expiry": self.expiry,
                "worker_id": "worker",
            }
        }


@pytest.mark.parametrize(
    "repository",
    [
        ElasticsearchReliabilityRepository,
        ElasticsearchSchemaIntelligenceRepository,
        ElasticsearchIntelligenceRepository,
    ],
)
def test_expired_and_superseded_workers_are_fenced(repository):
    def check(store, token):
        repo = repository(store)
        if repository is ElasticsearchReliabilityRepository:
            return repo._assert_fence("t:prod", token)
        if repository is ElasticsearchIntelligenceRepository:
            return repo.validate_fencing_token("t", "prod", token)
        return repo.validate_fence("t", "prod", token)

    check(LeaseStore(60), 7)
    with pytest.raises(StaleWriter, match="expired"):
        check(LeaseStore(-60), 7)
    with pytest.raises(StaleWriter, match="stale"):
        check(LeaseStore(60, token=8), 7)
