from ..normalisation import value


def bounded(items, limit, key):
    unique = {}
    for item in items:
        unique.setdefault(str(key(item)), item)
        if len(unique) >= limit:
            break
    return tuple(unique[k] for k in sorted(unique))
