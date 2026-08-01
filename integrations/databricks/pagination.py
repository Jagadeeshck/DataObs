from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from .errors import safe_error


@dataclass(frozen=True)
class Page:
    items: tuple[Any, ...]
    next_page_token: str | None = None


def collect_pages(
    fetch: Callable[[str | None], Page],
    *,
    key: Callable[[Any], str],
    maximum_pages: int,
    maximum_results: int,
    cancelled: Callable[[], bool] = lambda: False,
    deadline: float | None = None,
) -> list[Any]:
    token = None
    seen_tokens: set[str] = set()
    found: dict[str, Any] = {}
    for _ in range(maximum_pages):
        if cancelled():
            raise safe_error("statement_cancelled")
        if deadline is not None and monotonic() >= deadline:
            raise safe_error("request_timeout", retryable=True)
        page = fetch(token)
        for item in page.items:
            found.setdefault(key(item), item)
            if len(found) > maximum_results:
                raise safe_error("result_truncated")
        next_token = page.next_page_token
        if next_token is None:
            return [found[k] for k in sorted(found)]
        if not isinstance(next_token, str) or not next_token or len(next_token) > 4096:
            raise safe_error("pagination_token_invalid")
        if next_token in seen_tokens or next_token == token:
            raise safe_error("pagination_token_loop")
        seen_tokens.add(next_token)
        token = next_token
    raise safe_error("result_truncated")
