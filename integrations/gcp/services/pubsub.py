from __future__ import annotations

import fnmatch

from packages.collectors.sdk import PartialFailure

from ..evidence import subscription, topic


def _selected(name: str, include: tuple[str, ...], exclude: tuple[str, ...]) -> bool:
    short = name.rsplit("/", 1)[-1]
    return (not include or any(fnmatch.fnmatchcase(short, pattern) for pattern in include)) and not any(
        fnmatch.fnmatchcase(short, pattern) for pattern in exclude
    )


def _bounded(iterator, maximum: int, maximum_pages: int):
    count = 0
    for item in iterator:
        count += 1
        if count > maximum or count > maximum_pages * 1000:
            raise RuntimeError("pagination_limit_reached")
        yield item


def collect_project(context, cfg, project, publisher, subscriber):
    parent = f"projects/{project.project_id}"
    topics = []
    if cfg.pubsub["include_topics"]:
        for item in _bounded(
            publisher.invoke("list_topics", request={"project": parent}, timeout=cfg.limits["request_timeout_seconds"]),
            cfg.limits["maximum_topics_per_project"],
            cfg.limits["maximum_pages"],
        ):
            if _selected(str(item.name), project.include_topics, project.exclude_topics):
                observation = topic(context, project.project_id, item)
                topics.append(observation)
                yield observation
    visible = frozenset(item.native_resource_id for item in topics)
    if cfg.pubsub["include_subscriptions"]:
        for item in _bounded(
            subscriber.invoke(
                "list_subscriptions", request={"project": parent}, timeout=cfg.limits["request_timeout_seconds"]
            ),
            cfg.limits["maximum_subscriptions_per_project"],
            cfg.limits["maximum_pages"],
        ):
            if _selected(str(item.name), project.include_subscriptions, project.exclude_subscriptions):
                resource, dlq = subscription(context, project.project_id, item, visible)
                yield resource
                if dlq and cfg.pubsub["include_dead_letter_relationships"]:
                    yield dlq


def partial(code: str, capability: str = "metadata_collection") -> PartialFailure:
    return PartialFailure(
        capability,
        code,
        "Google Cloud Pub/Sub evidence is partially unavailable",
        code in {"request_timeout", "pubsub_api_unavailable"},
    )
