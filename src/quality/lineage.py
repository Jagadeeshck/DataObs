"""
DataObs — Data Lineage Tracker

Builds and queries the end-to-end data lineage graph.
Lineage nodes and edges are stored in Elasticsearch.
Supports auto-discovery from Glue job scripts, dbt manifests, and Airflow DAGs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from elasticsearch import Elasticsearch
from opentelemetry import trace
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("dataobs.lineage")


class NodeType(str, Enum):
    TABLE = "table"
    S3_PATH = "s3_path"
    LAMBDA = "lambda"
    GLUE_JOB = "glue_job"
    EMR_STEP = "emr_step"
    DBT_MODEL = "dbt_model"
    AIRFLOW_TASK = "airflow_task"
    KAFKA_TOPIC = "kafka_topic"
    API = "api"


@dataclass
class LineageNode:
    node_id: str                        # Unique identifier: e.g., "rds.prod.orders"
    node_type: NodeType
    name: str
    platform: str                       # aws | gcp | azure | on-prem
    environment: str                    # production | staging | dev
    tags: dict = field(default_factory=dict)
    description: Optional[str] = None
    owner: Optional[str] = None
    updated_at: Optional[str] = None

    def to_es_doc(self) -> dict:
        return {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "platform": self.platform,
            "environment": self.environment,
            "tags": self.tags,
            "description": self.description,
            "owner": self.owner,
        }


@dataclass
class LineageEdge:
    source_node_id: str
    target_node_id: str
    job_id: str                         # The job/process that created this edge
    job_type: str                       # glue_job | lambda | dbt | airflow | manual
    transformation: Optional[str] = None  # SQL or description of transform
    run_id: Optional[str] = None
    created_at: Optional[str] = None
    tags: dict = field(default_factory=dict)

    def to_es_doc(self) -> dict:
        return {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "job_id": self.job_id,
            "job_type": self.job_type,
            "transformation": self.transformation,
            "run_id": self.run_id,
            "tags": self.tags,
        }


class LineageTracker:
    """
    Stores and queries lineage nodes and edges in Elasticsearch.
    Provides impact analysis: given a source node, find all downstream consumers.
    """

    NODE_INDEX = "dataobs-lineage-nodes"
    EDGE_INDEX = "dataobs-lineage-edges"

    def __init__(self, es_client: Elasticsearch):
        self.es = es_client
        self._ensure_indices()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    def upsert_node(self, node: LineageNode) -> None:
        """Insert or update a lineage node.

        Uses the current elasticsearch-py 8.x keyword-argument API.
        The deprecated body= parameter has been replaced with doc= and
        doc_as_upsert= to prepare for the elasticsearch-py 9.x upgrade.
        """
        self.es.update(
            index=self.NODE_INDEX,
            id=node.node_id,
            doc=node.to_es_doc(),
            doc_as_upsert=True,
        )
        logger.debug("Upserted lineage node: %s", node.node_id)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    def record_edge(self, edge: LineageEdge) -> None:
        """Record a lineage edge (data flow between two nodes)."""
        self.es.index(
            index=self.EDGE_INDEX,
            document=edge.to_es_doc(),
        )
        logger.debug("Recorded lineage edge: %s -> %s", edge.source_node_id, edge.target_node_id)

    @tracer.start_as_current_span("get_downstream_impact")
    def get_downstream_impact(self, node_id: str, depth: int = 5) -> List[str]:
        """
        BFS traversal to find all downstream nodes affected by a change to node_id.
        Returns a list of affected node IDs in order of distance.

        Note: each hop fetches up to 100 edges. For nodes with >100 outgoing
        edges consider replacing with search_after pagination.
        """
        span = trace.get_current_span()
        span.set_attribute("dataobs.lineage.root_node", node_id)

        visited = set()
        queue = [node_id]
        affected = []
        current_depth = 0

        while queue and current_depth < depth:
            next_queue = []
            for current_node in queue:
                if current_node in visited:
                    continue
                visited.add(current_node)

                response = self.es.search(
                    index=self.EDGE_INDEX,
                    query={"term": {"source_node_id.keyword": current_node}},
                    size=100,
                    source=["target_node_id"],
                )
                for hit in response["hits"]["hits"]:
                    target = hit["_source"]["target_node_id"]
                    if target not in visited:
                        next_queue.append(target)
                        if target not in affected:
                            affected.append(target)

            queue = next_queue
            current_depth += 1

        span.set_attribute("dataobs.lineage.affected_count", len(affected))
        logger.info("Impact analysis for %s: %d downstream nodes affected", node_id, len(affected))
        return affected

    def get_upstream_lineage(self, node_id: str, depth: int = 5) -> List[str]:
        """Trace upstream sources for a given node (reverse BFS)."""
        visited = set()
        queue = [node_id]
        sources = []
        current_depth = 0

        while queue and current_depth < depth:
            next_queue = []
            for current_node in queue:
                if current_node in visited:
                    continue
                visited.add(current_node)

                response = self.es.search(
                    index=self.EDGE_INDEX,
                    query={"term": {"target_node_id.keyword": current_node}},
                    size=100,
                    source=["source_node_id"],
                )
                for hit in response["hits"]["hits"]:
                    source = hit["_source"]["source_node_id"]
                    if source not in visited:
                        next_queue.append(source)
                        if source not in sources:
                            sources.append(source)

            queue = next_queue
            current_depth += 1

        return sources

    def ingest_dbt_manifest(self, manifest_path: str, environment: str = "production") -> int:
        """
        Parse a dbt manifest.json and extract lineage nodes + edges.
        Returns count of edges recorded.
        """
        with open(manifest_path) as f:
            manifest = json.load(f)

        edge_count = 0
        nodes = manifest.get("nodes", {})

        for node_key, node_data in nodes.items():
            if not node_key.startswith("model."):
                continue

            node_id = (
                f"dbt.{node_data.get('database', 'unknown')}"
                f".{node_data.get('schema', 'unknown')}"
                f".{node_data.get('name', '')}"
            )
            node = LineageNode(
                node_id=node_id,
                node_type=NodeType.DBT_MODEL,
                name=node_data.get("name", ""),
                platform="dbt",
                environment=environment,
                description=node_data.get("description", ""),
                tags={"dbt_resource_type": node_data.get("resource_type", "")},
            )
            self.upsert_node(node)

            for parent_key in node_data.get("depends_on", {}).get("nodes", []):
                parent_data = nodes.get(parent_key, {})
                if not parent_data:
                    continue
                source_id = (
                    f"dbt.{parent_data.get('database','')}"
                    f".{parent_data.get('schema','')}"
                    f".{parent_data.get('name','')}"
                )
                edge = LineageEdge(
                    source_node_id=source_id,
                    target_node_id=node_id,
                    job_id=node_key,
                    job_type="dbt",
                    transformation=node_data.get("compiled_code", "")[:2000],
                )
                self.record_edge(edge)
                edge_count += 1

        logger.info("Ingested dbt manifest: %d edges recorded", edge_count)
        return edge_count

    def _ensure_indices(self) -> None:
        """Create Elasticsearch indices if they don't exist.

        Uses the current elasticsearch-py 8.x keyword-argument API.
        The deprecated body= parameter has been replaced with settings= and
        mappings= keyword arguments.
        """
        for index in [self.NODE_INDEX, self.EDGE_INDEX]:
            if not self.es.indices.exists(index=index):
                self.es.indices.create(
                    index=index,
                    settings={"number_of_shards": 1, "number_of_replicas": 1},
                    mappings={
                        "properties": {
                            "@timestamp": {"type": "date"},
                            "source_node_id": {"type": "keyword"},
                            "target_node_id": {"type": "keyword"},
                            "node_id": {"type": "keyword"},
                            "node_type": {"type": "keyword"},
                            "environment": {"type": "keyword"},
                            "platform": {"type": "keyword"},
                        }
                    },
                )
                logger.info("Created index: %s", index)
