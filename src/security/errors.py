class SecurityError(Exception):
    def __init__(self, reason_code: str, message: str, *, status_code: int = 401):
        super().__init__(message)
        self.reason_code = reason_code
        self.status_code = status_code
