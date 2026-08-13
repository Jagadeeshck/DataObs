from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .models import IncidentReview, ReviewSections, ReviewStatus, review_identity
from .policy import decide


class ReviewConflict(RuntimeError):
    pass


class ReviewImmutable(RuntimeError):
    pass


class InMemoryPostIncidentRepository:
    def __init__(self) -> None:
        self.reviews: dict[str, IncidentReview] = {}
        self.events: list[dict[str, Any]] = []

    def get(self, tenant: str, environment: str, review_id: str) -> IncidentReview | None:
        item = self.reviews.get(review_id)
        return deepcopy(item) if item and (item.tenant_id, item.environment) == (tenant, environment) else None

    def list(self, tenant: str, environment: str, incident_id: str) -> list[IncidentReview]:
        return deepcopy(
            sorted(
                (
                    x
                    for x in self.reviews.values()
                    if (x.tenant_id, x.environment, x.incident_id) == (tenant, environment, incident_id)
                ),
                key=lambda x: x.review_generation,
            )
        )

    def create(self, review: IncidentReview) -> IncidentReview:
        existing = self.reviews.get(review.review_id)
        if existing:
            return deepcopy(existing)
        self.reviews[review.review_id] = deepcopy(review)
        return deepcopy(review)

    def update(self, review: IncidentReview, expected_revision: int) -> IncidentReview:
        current = self.reviews.get(review.review_id)
        if current is None or current.revision != expected_revision:
            raise ReviewConflict("review revision conflict")
        review.revision += 1
        self.reviews[review.review_id] = deepcopy(review)
        return deepcopy(review)


class PostIncidentService:
    def __init__(self, repository: InMemoryPostIncidentRepository) -> None:
        self.repository = repository

    def create(
        self, incident: Any, *, owner: str, evidence_cutoff: datetime, timeline_event_ids: list[str]
    ) -> IncidentReview:
        existing = self.repository.list(incident.tenant_id, incident.environment, incident.id)
        active = next(
            (item for item in reversed(existing) if item.status in {ReviewStatus.DRAFT, ReviewStatus.IN_REVIEW}), None
        )
        if active:
            return active
        generation = len(existing) + 1
        now = datetime.now(timezone.utc)
        review = IncidentReview(
            review_id=review_identity(incident.tenant_id, incident.environment, incident.id, generation),
            tenant_id=incident.tenant_id,
            environment=incident.environment,
            incident_id=incident.id,
            review_generation=generation,
            supersedes=existing[-1].review_id if existing else None,
            requirement=decide(str(incident.severity)),
            owner=owner,
            incident_revision=f"{incident.seq_no}:{incident.primary_term}",
            evidence_cutoff=evidence_cutoff,
            timeline_cutoff=timeline_event_ids[-1] if timeline_event_ids else None,
            sections=ReviewSections(summary=incident.title, technical_impact=incident.impact_summary or ""),
            timeline_event_ids=timeline_event_ids[:200],
            created_at=now,
            updated_at=now,
        )
        return self.repository.create(review)

    def update_sections(
        self, tenant: str, environment: str, review_id: str, sections: ReviewSections, *, expected_revision: int
    ) -> IncidentReview:
        review = self.repository.get(tenant, environment, review_id)
        if not review:
            raise KeyError(review_id)
        if review.status == ReviewStatus.COMPLETED:
            raise ReviewImmutable("completed reviews are immutable")
        review.sections, review.updated_at = sections, datetime.now(timezone.utc)
        return self.repository.update(review, expected_revision)

    def transition(
        self, tenant: str, environment: str, review_id: str, status: ReviewStatus, *, actor: str, expected_revision: int
    ) -> IncidentReview:
        review = self.repository.get(tenant, environment, review_id)
        if not review:
            raise KeyError(review_id)
        if review.status == ReviewStatus.COMPLETED:
            raise ReviewImmutable("completed reviews are immutable")
        allowed = {(ReviewStatus.DRAFT, ReviewStatus.IN_REVIEW), (ReviewStatus.IN_REVIEW, ReviewStatus.COMPLETED)}
        if (review.status, status) not in allowed:
            raise ValueError("invalid review transition")
        if status == ReviewStatus.COMPLETED and any(
            entry.classification.value == "confirmed" and not entry.author for entry in review.sections.root_causes
        ):
            raise ValueError("confirmed root cause requires explicit actor")
        review.status, review.updated_at = status, datetime.now(timezone.utc)
        if status == ReviewStatus.COMPLETED:
            review.completed_at = review.updated_at
        return self.repository.update(review, expected_revision)

    def refresh_evidence(
        self,
        tenant: str,
        environment: str,
        review_id: str,
        *,
        incident_revision: str,
        evidence_cutoff: datetime,
        timeline_event_ids: list[str],
        expected_revision: int,
    ) -> IncidentReview:
        review = self.repository.get(tenant, environment, review_id)
        if not review:
            raise KeyError(review_id)
        if review.status == ReviewStatus.COMPLETED:
            raise ReviewImmutable("completed reviews are immutable")
        review.incident_revision, review.evidence_cutoff = incident_revision, evidence_cutoff
        review.timeline_event_ids, review.timeline_cutoff, review.source_changed = (
            timeline_event_ids[:200],
            timeline_event_ids[-1] if timeline_event_ids else None,
            False,
        )
        review.updated_at = datetime.now(timezone.utc)
        return self.repository.update(review, expected_revision)
