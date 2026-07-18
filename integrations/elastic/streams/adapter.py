from __future__ import annotations

from typing import Any


class StreamsAdapter:
    def __init__(self, client: Any, enabled: bool = False, limit: int = 100) -> None:
        self.client = client
        self.enabled = enabled
        self.limit = limit

    def list_streams(self) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        try:
            return (
                self.client.options(ignore_status=[404])
                .transport.perform_request("GET", "/_streams")
                .body.get("streams", [])[: self.limit]
            )
        except Exception:
            return []

    def stream_details(self, name: str) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "technical_preview": True}
        try:
            return self.client.options(ignore_status=[404]).transport.perform_request("GET", f"/_streams/{name}").body
        except Exception as exc:
            return {"available": False, "error": str(exc)[:200], "technical_preview": True}

    def significant_events(self, stream: str, start: str, end: str) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        return []
