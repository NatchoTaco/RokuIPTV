from pydantic import BaseModel


class ServiceCheck(BaseModel):
    status: str
    detail: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    setup_complete: bool
    checks: dict[str, ServiceCheck]
