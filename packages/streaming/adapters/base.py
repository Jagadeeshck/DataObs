from typing import Protocol

from ..capabilities import AdapterCapabilities


class StreamAdapter(Protocol):
    def capabilities(self) -> AdapterCapabilities: ...
