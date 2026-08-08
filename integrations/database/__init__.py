"""Engine-neutral relational database collector foundation v1."""

from .contracts import DatabaseIdentity, PartialCollectionFailure
from .execution import BoundedStatementExecutor
from .identifiers import quote_identifier, validate_identifier
from .safety import FixedStatementRegistry, Statement

__all__ = [
    "BoundedStatementExecutor",
    "DatabaseIdentity",
    "FixedStatementRegistry",
    "PartialCollectionFailure",
    "Statement",
    "quote_identifier",
    "validate_identifier",
]
