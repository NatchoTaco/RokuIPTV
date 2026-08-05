from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from streamforge_api.api.deps import get_current_admin, get_db, get_settings
from streamforge_api.core.config import Settings
from streamforge_api.models import User
from streamforge_api.schemas.channels import (
    ChannelGroupListResponse,
    ChannelListResponse,
    ChannelSourceCandidateListResponse,
    ChannelSummaryResponse,
    ChannelUpdateRequest,
    NormalizationJobCreateRequest,
    NormalizationJobResponse,
)
from streamforge_api.services.channels import ChannelService

router = APIRouter()


@router.get("", response_model=ChannelListResponse)
def list_channels(
    cursor: str | None = None,
    page_size: int | None = Query(default=None, ge=1, le=500),
    search: str | None = Query(default=None, max_length=120),
    source_id: str | None = None,
    group: str | None = Query(default=None, max_length=120),
    visibility_status: str | None = Query(default=None, max_length=80),
    content_type: str | None = Query(default=None, max_length=80),
    duplicate_status: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> ChannelListResponse:
    return ChannelService(db, settings).list_channels(
        cursor=cursor,
        page_size=page_size,
        search=search,
        source_id=source_id,
        group=group,
        visibility_status=visibility_status,
        content_type=content_type,
        duplicate_status=duplicate_status,
    )


@router.get("/groups", response_model=ChannelGroupListResponse)
def list_channel_groups(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> ChannelGroupListResponse:
    return ChannelService(db, settings).list_groups()


@router.post("/normalization-jobs", response_model=NormalizationJobResponse, status_code=202)
def create_normalization_job(
    payload: NormalizationJobCreateRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> NormalizationJobResponse:
    return ChannelService(db, settings).create_normalization_job(
        source_id=payload.source_id,
        profile=payload.profile,
        process_now=payload.process_now,
    )


@router.get("/normalization-jobs/{job_id}", response_model=NormalizationJobResponse)
def get_normalization_job(
    job_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> NormalizationJobResponse:
    return ChannelService(db, settings).get_normalization_job(job_id)


@router.post("/normalization-jobs/{job_id}/cancel", response_model=NormalizationJobResponse)
def cancel_normalization_job(
    job_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> NormalizationJobResponse:
    return ChannelService(db, settings).cancel_normalization_job(job_id)


@router.patch("/{raw_channel_id}", response_model=ChannelSummaryResponse)
def update_channel(
    raw_channel_id: str,
    payload: ChannelUpdateRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> ChannelSummaryResponse:
    return ChannelService(db, settings).update_channel(raw_channel_id, payload)


@router.get("/{raw_channel_id}/candidates", response_model=ChannelSourceCandidateListResponse)
def list_channel_source_candidates(
    raw_channel_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> ChannelSourceCandidateListResponse:
    return ChannelService(db, settings).list_source_candidates(raw_channel_id)
