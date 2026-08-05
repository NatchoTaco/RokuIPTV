from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from streamforge_api.api.deps import get_current_admin, get_db, get_settings
from streamforge_api.core.config import Settings
from streamforge_api.models import User
from streamforge_api.schemas.sources import (
    PlaylistImportHistoryResponse,
    PlaylistImportJobResponse,
)
from streamforge_api.services.source_import import SourceImportService

router = APIRouter()


@router.get("/imports", response_model=PlaylistImportHistoryResponse)
def import_history(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> PlaylistImportHistoryResponse:
    return SourceImportService(db, settings).list_import_history()


@router.get("/jobs/{job_id}", response_model=PlaylistImportJobResponse)
def import_job(
    job_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> PlaylistImportJobResponse:
    return SourceImportService(db, settings).get_job(job_id)


@router.get("/synthetic-demo.m3u", response_class=PlainTextResponse)
def synthetic_demo_playlist(_current_admin: User = Depends(get_current_admin)) -> str:
    return """#EXTM3U
# StreamForge synthetic demonstration playlist. These example URLs are not media providers.
#EXTINF:-1 tvg-id="demo.news" tvg-name="Demo News" tvg-logo="https://example.com/logos/news.png" group-title="Demo News",Demo News
https://example.com/streamforge/demo/news/master.m3u8
#EXTINF:-1 tvg-id="demo.weather" tvg-name="Demo Weather" group-title="Demo Local",Demo Weather
https://example.com/streamforge/demo/weather/master.m3u8
#EXTINF:-1 tvg-id="demo.culture" tvg-name="Demo Culture" group-title="Demo Arts",Demo Culture
https://example.com/streamforge/demo/culture/master.m3u8
"""
