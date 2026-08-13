from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from .models import RelationshipStatus
from .recurrence import IncidentFamily, IncidentFamilyMembership, IncidentRecurrence

MAX_CANDIDATE_POOL = 200
MAX_RESULTS = 20
ALLOWED_LOOKBACK_DAYS = (30, 90, 180, 365)
DEFAULT_LOOKBACK_DAYS = 90


class IntelligenceConflict(RuntimeError):
    pass


class InMemoryIntelligenceRepository:
    """Test/local adapter. Production runtime selects the Elasticsearch adapter."""

    def __init__(self) -> None:
        self.relationships: dict[str, IncidentRecurrence] = {}
        self.families: dict[str, IncidentFamily] = {}
        self.memberships: dict[str, IncidentFamilyMembership] = {}

    def put_candidate(self, item: IncidentRecurrence) -> IncidentRecurrence:
        existing = self.relationships.get(item.relationship_id)
        # Durable rejection/confirmation wins for an unchanged feature/scoring version.
        if (
            existing
            and existing.feature_version == item.feature_version
            and existing.status != RelationshipStatus.CANDIDATE
        ):
            return deepcopy(existing)
        if not existing:
            self.relationships[item.relationship_id] = deepcopy(item)
        elif existing.status == RelationshipStatus.CANDIDATE and (
            existing.scoring_version != item.scoring_version
            or existing.feature_version != item.feature_version
            or existing.reason_codes != item.reason_codes
            or existing.similarity_score != item.similarity_score
        ):
            item.revision = existing.revision + 1
            self.relationships[item.relationship_id] = deepcopy(item)
        return deepcopy(self.relationships[item.relationship_id])

    def decide(
        self, relationship_id: str, status: RelationshipStatus, *, actor: str, reason: str, expected_revision: int
    ) -> IncidentRecurrence:
        if status not in {RelationshipStatus.CONFIRMED, RelationshipStatus.REJECTED}:
            raise ValueError("only confirmation or rejection is an operator decision")
        current = self.relationships.get(relationship_id)
        if not current:
            raise KeyError(relationship_id)
        if current.revision != expected_revision:
            raise IntelligenceConflict("relationship revision conflict")
        if current.status == status:
            return deepcopy(current)
        if current.status != RelationshipStatus.CANDIDATE:
            raise IntelligenceConflict("relationship already decided")
        current.status, current.actor, current.decision_reason = status, actor, reason
        current.decision_at, current.revision = datetime.now(timezone.utc), current.revision + 1
        return deepcopy(current)

    def add_membership(self, item: IncidentFamilyMembership) -> IncidentFamilyMembership:
        existing = self.memberships.setdefault(item.membership_id, deepcopy(item))
        return deepcopy(existing)
