from dataclasses import dataclass


@dataclass(frozen=True)
class RabbitMqError(Exception):
    code: str
    endpoint_family: str = "management"
    retryable: bool = False
    status_category: str | None = None

    def __str__(self) -> str:
        return self.code


def error(code: str, family: str = "management", retryable: bool = False, status: str | None = None):
    return RabbitMqError(code, family, retryable, status)
