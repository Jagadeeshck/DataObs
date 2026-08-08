from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from .errors import safe_error

T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    items: tuple[T, ...]
    next_token: str | None = None


def collect_pages(
    fetch: Callable[[str | None], Page[T]],
    key: Callable[[T], str],
    *,
    maximum_pages: int,
    maximum_results: int,
    cancelled: Callable[[], bool] = lambda: False,
) -> tuple[T, ...]:
    token = None
    seen_tokens = set()
    values: dict[str, T] = {}
    for _ in range(maximum_pages):
        if cancelled():
            raise safe_error("query_cancelled")
        page = fetch(token)
        for item in page.items:
            values.setdefault(key(item), item)
            if len(values) >= maximum_results:
                return tuple(values[k] for k in sorted(values))
        new = page.next_token
        if not new:
            return tuple(values[k] for k in sorted(values))
        if new == token or new in seen_tokens:
            raise safe_error("pagination_token_loop")
        seen_tokens.add(new)
        token = new
    raise safe_error("result_truncated")
