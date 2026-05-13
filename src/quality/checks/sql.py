"""SQL identifier helpers shared by quality checks.

The quality checks build small aggregate queries against user-configured
datasets and columns. SQLAlchemy can bind values, but it cannot bind table or
column identifiers, so every interpolated identifier must be validated first.
These helpers intentionally accept only portable identifiers made of letters,
digits, underscores, and dots; checks can then safely extract table and column
names for simple warehouse queries while rejecting malicious or ambiguous input.
"""

from __future__ import annotations

import re
from typing import Iterable

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_SIMPLE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_sql_identifier(value: str, label: str = "identifier") -> str:
    """Return *value* when it is safe to interpolate as a SQL identifier.

    Dotted identifiers such as ``analytics.orders`` are accepted. Quoted names,
    expressions, semicolons, whitespace, and comments are rejected so callers do
    not accidentally allow SQL fragments through configuration.
    """

    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"Invalid SQL identifier for {label!r}: {value!r}. "
            "Use only letters, digits, underscores, and dots."
        )
    return value


def validate_simple_identifier(value: str, label: str = "identifier") -> str:
    """Return *value* when it is a single unqualified SQL identifier."""

    if not isinstance(value, str) or not _SIMPLE_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"Invalid SQL identifier for {label!r}: {value!r}. "
            "Use a single name with letters, digits, and underscores only."
        )
    return value


def table_name_from_dataset(dataset: str) -> str:
    """Return the physical table name from a dotted DataObs dataset name."""

    validate_sql_identifier(dataset, "dataset")
    return validate_simple_identifier(dataset.split(".")[-1], "dataset table name")


def validate_column_names(columns: Iterable[str]) -> list[str]:
    """Validate and return a list of simple column names."""

    return [validate_simple_identifier(column, "column") for column in columns]
