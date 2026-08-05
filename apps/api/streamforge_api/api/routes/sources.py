from __future__ import annotations

<<<<<<< HEAD
=======
from typing import cast

>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from streamforge_api.api.deps import get_current_admin, get_db, get_settings
from streamforge_api.core.config import Settings
from streamforge_api.models import User
from streamforge_api.schemas.common import MessageResponse
from streamforge_api.schemas.sources import (
<<<<<<< HEAD
=======
    ContentType,
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
    PlaylistImportHistoryResponse,
    PlaylistImportJobResponse,
    SourceCreateDemoRequest,
    SourceCreateUrlRequest,
    SourceCreatedResponse,
    SourceListResponse,
    SourceUpdateRequest,
    SourceValidateUrlRequest,
    SourceValidationResponse,
)
<<<<<<< HEAD
from streamforge_api.services.source_import import SourceImportService, copy_upload_to_bytes
=======
from streamforge_api.services.source_import import SourceImportService, copy_upload_to_path
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)

router = APIRouter()


@router.get("", response_model=SourceListResponse)
def list_sources(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> SourceListResponse:
    return SourceImportService(db, settings).list_sources()


@router.post("/validate-url", response_model=SourceValidationResponse)
def validate_url_source(
    payload: SourceValidateUrlRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> SourceValidationResponse:
<<<<<<< HEAD
    return SourceImportService(db, settings).validate_url_source(str(payload.url))
=======
    return SourceImportService(db, settings).validate_url_source(
        str(payload.url),
        enabled_content_types=payload.enabled_content_types,
    )
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)


@router.post("/validate-upload", response_model=SourceValidationResponse)
def validate_upload_source(
<<<<<<< HEAD
=======
    enabled_content_types: str = Form(default="live_tv"),
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> SourceValidationResponse:
<<<<<<< HEAD
    content = copy_upload_to_bytes(file, max_bytes=settings.source_max_playlist_bytes)
    return SourceImportService(db, settings).validate_uploaded_playlist(content)
=======
    service = SourceImportService(db, settings)
    stored_path = service.reserve_upload_path(file.filename or "playlist.m3u")
    try:
        copy_upload_to_path(file, stored_path, max_bytes=settings.source_max_playlist_bytes)
        return service.validate_uploaded_playlist_path(
            stored_path,
            enabled_content_types=parse_content_types(enabled_content_types),
        )
    finally:
        stored_path.unlink(missing_ok=True)
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)


@router.post("/m3u-url", response_model=SourceCreatedResponse, status_code=201)
def create_url_source(
    payload: SourceCreateUrlRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_admin: User = Depends(get_current_admin),
) -> SourceCreatedResponse:
    return SourceImportService(db, settings).create_url_source(
        name=payload.name,
        raw_url=str(payload.url),
        refresh_interval_minutes=payload.refresh_interval_minutes,
<<<<<<< HEAD
=======
        enabled_content_types=payload.enabled_content_types,
        confirm_large_import=payload.confirm_large_import,
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
        actor=current_admin,
    )


@router.post("/m3u-upload", response_model=SourceCreatedResponse, status_code=201)
def create_upload_source(
    name: str = Form(..., min_length=1, max_length=180),
    refresh_interval_minutes: int | None = Form(default=None),
<<<<<<< HEAD
=======
    enabled_content_types: str = Form(default="live_tv"),
    confirm_large_import: bool = Form(default=False),
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_admin: User = Depends(get_current_admin),
) -> SourceCreatedResponse:
<<<<<<< HEAD
    content = copy_upload_to_bytes(file, max_bytes=settings.source_max_playlist_bytes)
    return SourceImportService(db, settings).create_upload_source(
        name=name,
        filename=file.filename or "playlist.m3u",
        content=content,
        refresh_interval_minutes=refresh_interval_minutes,
=======
    service = SourceImportService(db, settings)
    stored_path = service.reserve_upload_path(file.filename or "playlist.m3u")
    copy_upload_to_path(file, stored_path, max_bytes=settings.source_max_playlist_bytes)
    return service.create_upload_source_from_path(
        name=name,
        filename=file.filename or "playlist.m3u",
        stored_path=stored_path,
        refresh_interval_minutes=refresh_interval_minutes,
        enabled_content_types=parse_content_types(enabled_content_types),
        confirm_large_import=confirm_large_import,
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
        actor=current_admin,
    )


@router.post("/demo", response_model=SourceCreatedResponse, status_code=201)
def create_demo_source(
    payload: SourceCreateDemoRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_admin: User = Depends(get_current_admin),
) -> SourceCreatedResponse:
    return SourceImportService(db, settings).create_demo_source(
        name=payload.name,
        refresh_interval_minutes=payload.refresh_interval_minutes,
<<<<<<< HEAD
=======
        enabled_content_types=payload.enabled_content_types,
        confirm_large_import=payload.confirm_large_import,
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
        actor=current_admin,
    )


<<<<<<< HEAD
=======
def parse_content_types(raw_value: str) -> list[ContentType]:
    allowed = {"live_tv", "movie", "series", "unknown"}
    return [
        cast(ContentType, content_type)
        for content_type in (item.strip() for item in raw_value.split(","))
        if content_type in allowed
    ] or [cast(ContentType, "live_tv")]


>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
@router.patch("/{source_id}", response_model=SourceListResponse)
def update_source(
    source_id: str,
    payload: SourceUpdateRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> SourceListResponse:
    service = SourceImportService(db, settings)
    service.update_source(
        source_id,
        is_enabled=payload.is_enabled,
        refresh_interval_minutes=payload.refresh_interval_minutes,
    )
    return service.list_sources()


@router.delete("/{source_id}", response_model=MessageResponse)
def delete_source(
    source_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> MessageResponse:
    SourceImportService(db, settings).delete_source(source_id)
    return MessageResponse(message="Source deleted.")


@router.post("/{source_id}/refresh", response_model=PlaylistImportJobResponse, status_code=202)
def refresh_source(
    source_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_admin: User = Depends(get_current_admin),
) -> PlaylistImportJobResponse:
    return SourceImportService(db, settings).queue_manual_refresh(source_id, actor=current_admin)


@router.get("/{source_id}/imports", response_model=PlaylistImportHistoryResponse)
def source_import_history(
    source_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> PlaylistImportHistoryResponse:
    return SourceImportService(db, settings).list_import_history(source_id=source_id)
