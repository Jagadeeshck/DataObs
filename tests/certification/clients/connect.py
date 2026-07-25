import os

from .base import HttpClient


class ConnectClient(HttpClient):
    def __init__(self, **context):
        super().__init__(os.getenv("CONNECT_URL", "http://127.0.0.1:18083"), **context)
