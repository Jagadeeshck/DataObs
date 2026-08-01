import re

SECRET = re.compile(r"secret|password|token|credential|key", re.I)


def normalise_tags(tags, *, maximum=50):
    result = {}
    source = tags.items() if isinstance(tags, dict) else ((t.get("Key"), t.get("Value")) for t in tags or ())
    for key, value in sorted(source, key=lambda pair: str(pair[0]))[:maximum]:
        if key and not SECRET.search(str(key)):
            result[str(key)[:128]] = str(value)[:256]
    return result


def included(tags, filters):
    include, exclude = filters.get("include_tags", {}), filters.get("exclude_tags", {})
    return all(tags.get(k) in values for k, values in include.items()) and not any(
        tags.get(k) in values for k, values in exclude.items()
    )


def owner(tags, keys):
    return next((tags[k] for k in keys if tags.get(k)), None)
