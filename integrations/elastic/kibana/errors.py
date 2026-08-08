class KibanaError(RuntimeError):
    """A bounded error which never contains provider bodies or credentials."""

    def __init__(self, code: str, status: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


class KibanaOutcomeUnknown(KibanaError):
    pass
