"""Safe, reusable Integration SDK foundation for distributed SQL engines."""

from .contracts import EngineIdentity, PartialCollectionFailure
from .execution import BoundedExecutor, ExecutionResult
from .identifiers import quote_identifier, validate_identifier
from .safety import FixedStatement, FixedStatementRegistry

__all__ = [
    "BoundedExecutor",
    "EngineIdentity",
    "ExecutionResult",
    "FixedStatement",
    "FixedStatementRegistry",
    "PartialCollectionFailure",
    "quote_identifier",
    "validate_identifier",
]
