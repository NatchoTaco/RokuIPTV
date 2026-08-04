from fastapi import APIRouter, Depends
from pydantic import BaseModel

from streamforge_api.api.deps import get_settings
from streamforge_api.core.config import Settings

router = APIRouter()


class PublicSettingsResponse(BaseModel):
    app_name: str
    version: str
    environment: str


@router.get("/public", response_model=PublicSettingsResponse)
def public_settings(settings: Settings = Depends(get_settings)) -> PublicSettingsResponse:
    return PublicSettingsResponse(
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.env,
    )
