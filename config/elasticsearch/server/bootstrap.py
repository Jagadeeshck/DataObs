"""
DataObs — Server-Side Elasticsearch Bootstrap

Run once after the OpenSearch domain is active to:
1. Create the ILM policy
2. Create all index templates
3. Create the ingest pipeline
4. Create the snapshot repository (S3)
5. Create the snapshot lifecycle policy (SLM)

Usage:
  export ELASTIC_ENDPOINT=https://...
  export ELASTIC_USER=admin
  export ELASTIC_PASSWORD=...
  export SNAPSHOT_S3_BUCKET=dataobs-es-snapshots-<account_id>
  export AWS_REGION=eu-west-1
  python config/elasticsearch/server/bootstrap.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import boto3
from elasticsearch import Elasticsearch
from elasticsearch import exceptions as es_exceptions

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("dataobs.bootstrap.server")

BASE = Path(__file__).parent


def get_client() -> Elasticsearch:
    endpoint = os.environ["ELASTIC_ENDPOINT"]
    user = os.environ["ELASTIC_USER"]
    password = os.environ["ELASTIC_PASSWORD"]
    return Elasticsearch(
        endpoint,
        basic_auth=(user, password),
        verify_certs=True,
        ssl_show_warn=False,
    )


def bootstrap_ilm(es: Elasticsearch) -> None:
    policy = json.loads((BASE / "ilm-policy.json").read_text())
    es.ilm.put_lifecycle(name="dataobs-server-ilm", policy={"phases": policy["phases"]})
    log.info("ILM policy 'dataobs-server-ilm' applied")


def bootstrap_index_templates(es: Elasticsearch) -> None:
    templates_doc = json.loads((BASE / "index-templates.json").read_text())
    for tpl in templates_doc["templates"]:
        name = tpl.pop("name")
        es.indices.put_index_template(
            name=name,
            index_patterns=tpl["index_patterns"],
            data_stream=tpl.get("data_stream", {}),
            priority=tpl.get("priority", 200),
            template=tpl.get("template", {}),
        )
        log.info("Index template '%s' applied", name)


def bootstrap_ingest_pipeline(es: Elasticsearch) -> None:
    pipeline_doc = json.loads((BASE / "ingest-pipeline.json").read_text())
    for pipeline in pipeline_doc["pipelines"]:
        name = pipeline.pop("name")
        es.ingest.put_pipeline(id=name, processors=pipeline["processors"], on_failure=pipeline.get("on_failure", []))
        log.info("Ingest pipeline '%s' applied", name)


def bootstrap_snapshot_repo(es: Elasticsearch) -> None:
    bucket = os.environ["SNAPSHOT_S3_BUCKET"]
    region = os.environ.get("AWS_REGION", "eu-west-1")
    es.snapshot.create_repository(
        name="dataobs-s3",
        repository={
            "type": "s3",
            "settings": {
                "bucket": bucket,
                "region": region,
                "server_side_encryption": True,
                "base_path": "elasticsearch/",
            },
        },
    )
    log.info("Snapshot repository 'dataobs-s3' registered (bucket=%s)", bucket)


def bootstrap_slm(es: Elasticsearch) -> None:
    """Snapshot Lifecycle Management — nightly at 01:00 UTC."""
    es.slm.put_lifecycle(
        policy_id="dataobs-nightly",
        schedule="0 0 1 * * ?",
        name="dataobs-snap-{now/d}",
        repository="dataobs-s3",
        config={
            "indices": ["dataobs-*"],
            "ignore_unavailable": True,
            "include_global_state": False,
        },
        retention={
            "expire_after": "30d",
            "min_count": 5,
            "max_count": 30,
        },
    )
    log.info("SLM policy 'dataobs-nightly' applied")


def main() -> None:
    log.info("Connecting to Elasticsearch...")
    es = get_client()
    info = es.info()
    log.info("Connected: %s %s", info["name"], info["version"]["number"])

    bootstrap_ilm(es)
    bootstrap_index_templates(es)
    bootstrap_ingest_pipeline(es)
    bootstrap_snapshot_repo(es)
    bootstrap_slm(es)

    log.info("Server-side bootstrap complete.")


if __name__ == "__main__":
    try:
        main()
    except es_exceptions.ConnectionError as e:
        log.error("Cannot connect to Elasticsearch: %s", e)
        sys.exit(1)
    except KeyError as e:
        log.error("Missing required environment variable: %s", e)
        sys.exit(1)
