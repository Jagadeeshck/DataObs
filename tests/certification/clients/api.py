import os

from .base import HttpClient


class ApiClient(HttpClient):
    def __init__(self, **context):
        super().__init__(os.getenv("DATAOBS_API_URL", "http://127.0.0.1:18000"), **context)
