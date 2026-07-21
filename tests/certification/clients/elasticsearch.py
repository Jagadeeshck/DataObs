import os

from .base import HttpClient


class ElasticsearchClient(HttpClient):
    def __init__(self, **context):
        super().__init__(os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:19200"), **context)
