from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from streamforge_api.api.deps import get_current_admin, get_db, get_settings
from streamforge_api.core.config import Settings
from streamforge_api.models import User
from streamforge_api.schemas.channels import (
    ClearProtectionsResponse,
    CleanupApplyResponse,
    CleanupPreviewResponse,
    CleanupProfileRequest,
    CleanupQueuesResponse,
    DuplicateActionResponse,
    DuplicateClusterListResponse,
    ProtectionSummaryResponse,
)
from streamforge_api.services.channels import ChannelService

router = APIRouter()


@router.get("/queues", response_model=CleanupQueuesResponse)
def cleanup_queues(
    source_id: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> CleanupQueuesResponse:
    return ChannelService(db, settings).cleanup_queues(source_id=source_id)


@router.post("/preview", response_model=CleanupPreviewResponse)
def preview_cleanup_profile(
    payload: CleanupProfileRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> CleanupPreviewResponse:
    return ChannelService(db, settings).preview_cleanup_profile(
        profile=payload.profile,
        source_id=payload.source_id,
    )


@router.post("/apply", response_model=CleanupApplyResponse)
def apply_cleanup_profile(
    payload: CleanupProfileRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> CleanupApplyResponse:
    return ChannelService(db, settings).apply_cleanup_profile(
        profile=payload.profile,
        source_id=payload.source_id,
    )


@router.get("/protections", response_model=ProtectionSummaryResponse)
def protection_summary(
    source_id: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> ProtectionSummaryResponse:
    return ChannelService(db, settings).protection_summary(source_id=source_id)


@router.post("/protections/clear", response_model=ClearProtectionsResponse)
def clear_manual_protections(
    source_id: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> ClearProtectionsResponse:
    return ChannelService(db, settings).clear_manual_protections(source_id=source_id)


@router.get("/duplicates", response_model=DuplicateClusterListResponse)
def duplicate_clusters(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> DuplicateClusterListResponse:
    return ChannelService(db, settings).list_duplicate_clusters()


@router.post("/duplicates/{cluster_id}/merge", response_model=DuplicateActionResponse)
def merge_duplicate_cluster(
    cluster_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> DuplicateActionResponse:
    return ChannelService(db, settings).merge_duplicate_cluster(cluster_id)


@router.post("/duplicates/{cluster_id}/split", response_model=DuplicateActionResponse)
def split_duplicate_cluster(
    cluster_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> DuplicateActionResponse:
    return ChannelService(db, settings).split_duplicate_cluster(cluster_id)


@router.post("/duplicates/{cluster_id}/protect", response_model=DuplicateActionResponse)
def protect_duplicate_cluster(
    cluster_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> DuplicateActionResponse:
    return ChannelService(db, settings).protect_duplicate_cluster(cluster_id)


@router.post("/duplicates/{cluster_id}/unprotect", response_model=DuplicateActionResponse)
def unprotect_duplicate_cluster(
    cluster_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_admin: User = Depends(get_current_admin),
) -> DuplicateActionResponse:
    return ChannelService(db, settings).unprotect_duplicate_cluster(cluster_id)
