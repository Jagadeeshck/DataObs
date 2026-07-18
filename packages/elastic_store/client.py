from __future__ import annotations

import os

from elasticsearch import Elasticsearch


def make_client() -> Elasticsearch:
    return Elasticsearch(
        [os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")],
        basic_auth=(os.getenv("ELASTICSEARCH_USER", "elastic"), os.getenv("ELASTICSEARCH_PASSWORD", "")),
        request_timeout=30,
    )
