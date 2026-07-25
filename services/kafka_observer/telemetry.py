from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


@contextmanager
def collection_span(name: str) -> Iterator[None]:
    """Dependency-free span boundary; an installed OTel SDK may instrument this call site."""
    del name
    yield
