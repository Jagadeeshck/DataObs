from dataclasses import dataclass


@dataclass(frozen=True)
class GoogleCloudCollectorError(Exception):
    code: str
    family: str = "gcp"
    retryable: bool = False

    def __str__(self) -> str:
        return self.code


def error(code: str, family: str = "gcp", retryable: bool = False) -> GoogleCloudCollectorError:
    return GoogleCloudCollectorError(code, family, retryable)
