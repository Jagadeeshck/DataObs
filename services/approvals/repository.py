from __future__ import annotations

from typing import Protocol

from .service import ApprovalRequest


class ApprovalRepository(Protocol):
    def get(self, tenant_id: str, approval_id: str) -> ApprovalRequest | None: ...
    def save(self, approval: ApprovalRequest) -> ApprovalRequest: ...


class InMemoryApprovalRepository:
    """Test-only repository; production must bind an Elasticsearch implementation."""

    def __init__(self) -> None:
        self.items: dict[str, ApprovalRequest] = {}

    def get(self, tenant_id: str, approval_id: str) -> ApprovalRequest | None:
        item = self.items.get(approval_id)
        return item if item and item.tenant_id == tenant_id else None

    def save(self, approval: ApprovalRequest) -> ApprovalRequest:
        self.items[approval.id] = approval
        return approval
