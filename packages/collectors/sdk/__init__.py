"""Typed provider Integration SDK v1."""

from .base import IntegrationProvider
from .capabilities import Capability, CollectionMode, ProviderCapabilities
from .checkpoints import CollectionCheckpoint, InMemoryCheckpointStore, PaginationCursor
from .configuration import CredentialReference, CredentialReferenceType, IntegrationConfiguration
from .context import IntegrationContext
from .discovery import CollectionRequest, DiscoveryRequest
from .observations import (
    CollectionRunResult,
    EvidenceState,
    HealthObservation,
    MetricObservation,
    PartialFailure,
    ProviderObservation,
    ResourceObservation,
    canonical_resource_id,
)
from .registry import ProviderRegistry
from .retry import RetryPolicy, with_retry
from .validation import ConnectionTestResult, ValidationIssue, ValidationResult

__all__ = [
    "Capability",
    "CollectionCheckpoint",
    "CollectionMode",
    "CollectionRequest",
    "ConnectionTestResult",
    "CredentialReference",
    "CredentialReferenceType",
    "DiscoveryRequest",
    "EvidenceState",
    "HealthObservation",
    "InMemoryCheckpointStore",
    "IntegrationConfiguration",
    "IntegrationContext",
    "IntegrationProvider",
    "MetricObservation",
    "CollectionRunResult",
    "PartialFailure",
    "PaginationCursor",
    "ProviderCapabilities",
    "ProviderObservation",
    "ProviderRegistry",
    "ResourceObservation",
    "RetryPolicy",
    "ValidationIssue",
    "ValidationResult",
    "canonical_resource_id",
    "with_retry",
]
