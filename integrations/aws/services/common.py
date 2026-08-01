from datetime import datetime, timezone

from packages.collectors.sdk import ResourceObservation

from ..tagging import included, normalise_tags, owner


def observation(context, cfg, account, region, service, kind, native_id, name, safe, tags=()):
    normal = normalise_tags(tags)
    if not included(normal, cfg.raw.get("resource_filters") or {}):
        return None
    return ResourceObservation(
        "aws",
        account,
        region,
        service,
        kind,
        str(native_id),
        str(name),
        datetime.now(timezone.utc),
        context.collection_run_id,
        normal,
        owner(normal, cfg.raw.get("ownership_tag_keys") or ()),
        safe,
        1.0,
    )


def pages(client, method, key, *, token="Marker", output_token="Marker", maximum=100, **kwargs):
    for _ in range(maximum):
        response = getattr(client, method)(**kwargs)
        for item in response.get(key, ()):
            yield item
        value = response.get(output_token)
        if not value:
            return
        kwargs[token] = value
