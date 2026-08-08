"""Bounded, space-aware Kibana integration boundary."""

from .client import KibanaClient
from .configuration import KibanaConfiguration

__all__ = ["KibanaClient", "KibanaConfiguration"]
