PRIMARY_TARGET = "RabbitMQ 4.3.x"
TESTED_VERSION = "unit fixtures compatible with RabbitMQ Management HTTP API 4.3"


def supported_version(version: str) -> bool:
    try:
        major, minor, *_ = (int(part) for part in version.split("."))
    except ValueError:
        return False
    return (major, minor) >= (4, 2)
