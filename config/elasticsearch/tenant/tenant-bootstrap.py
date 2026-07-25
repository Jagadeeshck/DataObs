"""
DataObs — Tenant-Side Elasticsearch Bootstrap

Run once per new tenant after the tenant OpenSearch domain is active.
This script:
1. Creates a read-only tenant role with document-level security (DLS)
   restricting visibility to dataobs.tenant_id == <tenant_id>
2. Creates a tenant API key scoped to that role
3. Registers the server cluster as a remote for Cross-Cluster Replication (CCR)
4. Creates CCR auto-follow patterns for quality-results and lineage indices
5. Stores the API key in AWS Secrets Manager

Usage:
  export TENANT_ID=acme
  export TENANT_ES_ENDPOINT=https://...
  export TENANT_ES_USER=admin
  export TENANT_ES_PASSWORD=...
  export SERVER_ES_ENDPOINT=https://...
  export SERVER_ES_USER=admin
  export SERVER_ES_PASSWORD=...
  export AWS_REGION=eu-west-1
  python config/elasticsearch/tenant/tenant-bootstrap.py
"""

from __future__ import annotations

import json
import logging
import os
import sys

import boto3
from elasticsearch import Elasticsearch
from elasticsearch import exceptions as es_exceptions

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("dataobs.bootstrap.tenant")


def get_client(endpoint: str, user: str, password: str) -> Elasticsearch:
    return Elasticsearch(
        endpoint,
        basic_auth=(user, password),
        verify_certs=True,
    )


def create_tenant_role(es: Elasticsearch, tenant_id: str) -> None:
    """
    Create a read-only role with document-level security (DLS).
    The DLS query restricts documents to those where
    dataobs.tenant_id matches this tenant's ID exactly.
    This prevents one tenant from reading another tenant's data
    even if they share the same index.
    """
    role_name = f"dataobs-tenant-{tenant_id}-readonly"
    es.security.put_role(
        name=role_name,
        cluster=["monitor"],
        indices=[
            {
                "names": [
                    "dataobs-quality-results-*",
                    "dataobs-lineage-*",
                    "dataobs-freshness-*",
                    "dataobs-traces-*",
                    "dataobs-metrics-*",
                ],
                "privileges": ["read", "view_index_metadata"],
                "query": json.dumps({"term": {"dataobs.tenant_id": tenant_id}}),
            }
        ],
    )
    log.info("Created DLS role '%s' for tenant '%s'", role_name, tenant_id)


def create_tenant_api_key(es: Elasticsearch, tenant_id: str) -> str:
    """Create a scoped API key for the tenant's OTel collector."""
    role_name = f"dataobs-tenant-{tenant_id}-readonly"
    response = es.security.create_api_key(
        name=f"dataobs-tenant-{tenant_id}-otel",
        role_descriptors={
            role_name: {
                "cluster": ["monitor"],
                "index": [
                    {
                        "names": ["dataobs-*"],
                        "privileges": ["read", "view_index_metadata"],
                        "query": json.dumps({"term": {"dataobs.tenant_id": tenant_id}}),
                    }
                ],
            }
        },
        expiration="365d",
    )
    encoded = response["encoded"]
    log.info("Created API key for tenant '%s' (id=%s)", tenant_id, response["id"])
    return encoded


def register_remote_cluster(es: Elasticsearch, server_endpoint: str) -> None:
    """
    Register the DataObs server cluster as a remote cluster
    on the tenant domain. This enables CCR pull replication.
    server_endpoint should be just the host:port (no https://).
    """
    host = server_endpoint.replace("https://", "").rstrip("/")
    es.cluster.put_settings(
        persistent={
            "cluster": {
                "remote": {
                    "dataobs-server": {
                        "seeds": [f"{host}:9300"],
                        "transport.ping_schedule": "30s",
                    }
                }
            }
        }
    )
    log.info("Registered remote cluster 'dataobs-server' -> %s", host)


def create_ccr_auto_follow(es: Elasticsearch, tenant_id: str) -> None:
    """
    Auto-follow patterns replicate matching indices from the server cluster
    into this tenant domain automatically as new indices are created.
    Only quality-results and lineage indices are replicated to tenants;
    raw traces and logs stay on the server cluster only.
    """
    es.ccr.put_auto_follow_pattern(
        name=f"dataobs-quality-{tenant_id}",
        remote_cluster="dataobs-server",
        leader_index_patterns=[
            "dataobs-quality-results-*",
            "dataobs-lineage-nodes",
            "dataobs-lineage-edges",
            "dataobs-freshness-*",
        ],
        follow_index_pattern="{{leader_index}}-replicated",
        settings={"index.number_of_replicas": 0},  # Single-node tenant, no replicas needed
    )
    log.info(
        "CCR auto-follow pattern 'dataobs-quality-%s' registered (remote=dataobs-server)",
        tenant_id,
    )


def store_api_key_in_secrets_manager(tenant_id: str, api_key: str, region: str) -> None:
    """Write the tenant API key to Secrets Manager for retrieval by the OTel collector."""
    client = boto3.client("secretsmanager", region_name=region)
    secret_name = f"dataobs/tenants/{tenant_id}/otel-api-key"
    try:
        client.create_secret(
            Name=secret_name,
            Description=f"DataObs tenant {tenant_id} OTel collector API key",
            SecretString=json.dumps({"api_key": api_key, "tenant_id": tenant_id}),
        )
        log.info("API key stored in Secrets Manager: %s", secret_name)
    except client.exceptions.ResourceExistsException:
        client.update_secret(
            SecretId=secret_name, SecretString=json.dumps({"api_key": api_key, "tenant_id": tenant_id})
        )
        log.info("API key updated in Secrets Manager: %s", secret_name)


def main() -> None:
    tenant_id = os.environ["TENANT_ID"]
    tenant_endpoint = os.environ["TENANT_ES_ENDPOINT"]
    server_endpoint = os.environ["SERVER_ES_ENDPOINT"]
    region = os.environ.get("AWS_REGION", "eu-west-1")

    log.info("Bootstrapping tenant '%s'...", tenant_id)

    tenant_es = get_client(
        tenant_endpoint,
        os.environ["TENANT_ES_USER"],
        os.environ["TENANT_ES_PASSWORD"],
    )
    server_es = get_client(
        server_endpoint,
        os.environ["SERVER_ES_USER"],
        os.environ["SERVER_ES_PASSWORD"],
    )

    # Step 1: Create DLS role on tenant cluster
    create_tenant_role(tenant_es, tenant_id)

    # Step 2: Create scoped API key on tenant cluster
    api_key = create_tenant_api_key(tenant_es, tenant_id)

    # Step 3: Register server as remote cluster on tenant domain
    register_remote_cluster(tenant_es, server_endpoint)

    # Step 4: Set up CCR auto-follow from server -> tenant
    create_ccr_auto_follow(tenant_es, tenant_id)

    # Step 5: Store API key in Secrets Manager
    store_api_key_in_secrets_manager(tenant_id, api_key, region)

    log.info("Tenant bootstrap complete for '%s'.", tenant_id)


if __name__ == "__main__":
    try:
        main()
    except es_exceptions.ConnectionError as e:
        log.error("Cannot connect to Elasticsearch: %s", e)
        sys.exit(1)
    except KeyError as e:
        log.error("Missing required environment variable: %s", e)
        sys.exit(1)
