"""Safe, structured errors returned by the canonical dbt artifact boundary."""


class DbtArtifactError(ValueError):
    def __init__(self, code: str, message: str, **details: object) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.details = details


class UnsupportedSchemaVersion(DbtArtifactError):
    def __init__(self, detected: str, supported: tuple[str, ...]) -> None:
        super().__init__(
            "unsupported_schema_version",
            "The dbt artifact schema version is not supported",
            detected=detected[:256],
            supported=list(supported),
        )
