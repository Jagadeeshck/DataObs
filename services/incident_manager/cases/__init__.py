"""Elastic Cases collaboration projection; incidents remain authoritative."""

from .contracts import CaseLink, CaseLinkState, CaseProviderState
from .service import CaseService

__all__ = ["CaseLink", "CaseLinkState", "CaseProviderState", "CaseService"]
