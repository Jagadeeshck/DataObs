from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    items: tuple[dict, ...]
    page: int
    page_count: int


def decode_page(payload, page):
    if isinstance(payload, list):
        return Page(tuple(payload), page, page)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("invalid paginated response")
    page_count = payload.get("page_count", page)
    if not isinstance(page_count, int) or page_count < page:
        page_count = page
    return Page(tuple(payload["items"]), page, page_count)
