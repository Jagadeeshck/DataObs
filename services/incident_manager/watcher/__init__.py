"""Team 3 Watcher-driven alerting: ES _watcher lifecycle + firing-watch mapping.

This package registers/deregisters Elasticsearch Watcher watches as an alert
source and maps a firing watch into the existing deduplicating incident
pipeline. It never sends a real pager/ticket/notification itself and never
performs autonomous remediation; delivery stays with the existing dispatcher
and all response remains approval-bound.
"""

from .lifecycle import (  # noqa: F401
    WatchLifecycleManager,
    WatchLifecycleResult,
    WatchRegistration,
)
from .trigger import (  # noqa: F401
    WatchTriggerError,
    map_watch_firing_to_event,
)
