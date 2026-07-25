import os

from .base import HttpClient


class SchemaRegistryClient(HttpClient):
    def __init__(self, **context):
        super().__init__(os.getenv("SCHEMA_REGISTRY_URL", "http://127.0.0.1:18081"), **context)
