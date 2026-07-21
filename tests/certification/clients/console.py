import os

from .base import HttpClient


class ConsoleClient(HttpClient):
    def __init__(self, **context):
        super().__init__(os.getenv("PLAYWRIGHT_BASE_URL", "http://127.0.0.1:18080"), **context)
