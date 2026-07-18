from pydantic import BaseModel


class ErrorContract(BaseModel):
    code: str
    message: str
    correlation_id: str | None = None
    details: dict = {}
