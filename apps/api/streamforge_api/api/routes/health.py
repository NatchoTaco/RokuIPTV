from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from streamforge_api.api.deps import get_db, get_settings
from streamforge_api.core.config import Settings
from streamforge_api.schemas.health import HealthResponse
from streamforge_api.services.health import HealthService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    return HealthService(db, settings, request.app.state.redis_client).collect()


@router.get("/readiness", response_model=HealthResponse)
def readiness(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse | JSONResponse:
    health_response = HealthService(db, settings, request.app.state.redis_client).collect()
    if health_response.status != "ok":
        return JSONResponse(status_code=503, content=health_response.model_dump(mode="json"))
    return health_response
