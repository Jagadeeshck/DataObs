"""
DataObs Quality Checks

All check implementations are registered here.
"""
from .null_check import NullCheck
from .row_count_check import RowCountCheck
from .uniqueness_check import UniquenessCheck
from .schema_check import SchemaCheck
from .referential_integrity_check import ReferentialIntegrityCheck
from .value_range_check import ValueRangeCheck

CHECK_REGISTRY = {
    "null_check": NullCheck,
    "row_count": RowCountCheck,
    "uniqueness": UniquenessCheck,
    "schema_change": SchemaCheck,
    "referential_integrity": ReferentialIntegrityCheck,
    "value_range": ValueRangeCheck,
}

__all__ = list(CHECK_REGISTRY.keys()) + ["CHECK_REGISTRY"]
