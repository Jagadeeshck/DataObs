"""Command Center projector — real six-pillar aggregation for the Console estate view.

The Console's Command Center reads a single durable projection
(`dataobs-command-center-summary-v1`). Nothing produced that projection before, so the
estate view was always empty. This service is the producer: it reads the authoritative
per-pillar read-models (incidents, quality, freshness, lineage, streams) and computes a
tenant/environment-scoped six-pillar health summary plus a priority work queue.

Design:
- `aggregate_summary` is pure (plain inputs → summary dict), so pillar health and queue
  logic are unit-tested without Elasticsearch.
- `CommandCenterProjector` wires the pure aggregator to the ES read-models and the write
  alias.

Honesty contract (matches the rest of the product):
- A pillar with no observations is `unknown`, never `healthy`.
- A measured zero (e.g. 0 open incidents, observed) is distinct from missing evidence.
- `data_status.complete` is true only when every contributing source answered.
"""

from .aggregator import PILLARS, aggregate_summary
from .projector import CommandCenterProjector

__all__ = ["aggregate_summary", "PILLARS", "CommandCenterProjector"]
