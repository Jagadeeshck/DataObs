from .errors import safe_error


def bounded(items, maximum_pages, maximum_resources, key=lambda x: id(x), context=None):
    seen = set()
    count = 0
    pages = 0
    by_page = getattr(items, "by_page", None)
    streams = by_page() if by_page else (items,)
    for page in streams:
        pages += 1
        if pages > maximum_pages:
            raise safe_error("result_truncated")
        for item in page:
            if context is not None and context.remaining_seconds <= 0:
                raise safe_error("request_timeout", True)
            identity = str(key(item))
            if identity in seen:
                continue
            seen.add(identity)
            count += 1
            if count > maximum_resources:
                raise safe_error("result_truncated")
            yield item
