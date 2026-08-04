from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from streamforge_api.api.deps import get_current_admin, get_db, get_settings
from streamforge_api.core.config import Settings
from streamforge_api.models import User
from streamforge_api.services.health import HealthService

router = APIRouter()


class DiagnosticsSummaryResponse(BaseModel):
    status: str
    version: str
    checks: dict[str, str]


@router.get("/summary", response_model=DiagnosticsSummaryResponse)
def diagnostics_summary(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> DiagnosticsSummaryResponse:
    health = HealthService(db, settings, request.app.state.redis_client).collect()
    return DiagnosticsSummaryResponse(
        status=health.status,
        version=health.version,
        checks={name: check.status for name, check in health.checks.items()},
    )
