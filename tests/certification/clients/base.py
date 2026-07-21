"""Bounded, redacting HTTP primitives for hosted certification."""

from __future__ import annotations

import json
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LiveServiceError(AssertionError):
    pass


class HttpClient:
    def __init__(self, base_url: str, *, tenant: str = "tenant-alpha", environment: str = "staging"):
        self.base_url = base_url.rstrip("/")
        self.tenant = tenant
        self.environment = environment

    def request(self, path: str, *, method: str = "GET", body=None, expected=(200,)):
        headers = {
            "X-DataObs-Tenant": self.tenant,
            "X-DataObs-Environment": self.environment,
            "X-Request-ID": str(uuid.uuid4()),
        }
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        try:
            with urlopen(
                Request(self.base_url + path, data=data, headers=headers, method=method), timeout=10
            ) as response:
                payload = response.read(2_000_000)
                status = response.status
        except HTTPError as error:
            payload = error.read(4096)
            status = error.code
        except (URLError, TimeoutError) as error:
            raise LiveServiceError(f"service unreachable at {self.base_url}: {type(error).__name__}") from None
        if status not in expected:
            raise LiveServiceError(f"{method} {path} returned {status}; response withheld")
        try:
            return json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            return payload.decode(errors="replace")

    def wait(self, path: str, predicate=lambda value: bool(value), *, deadline_seconds=60):
        deadline = time.monotonic() + deadline_seconds
        last = None
        while time.monotonic() < deadline:
            try:
                last = self.request(path)
                if predicate(last):
                    return last
            except LiveServiceError as error:
                last = error
            time.sleep(2)
        raise LiveServiceError(f"deadline exceeded for {path}; last result type={type(last).__name__}")
