from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ContentType = Literal["live_tv", "movie", "series", "unknown"]
FilterProfile = Literal["light", "recommended", "aggressive", "custom"]
JobStatus = Literal["queued", "running", "succeeded", "failed", "canceled"]
VisibilityStatus = Literal["visible", "hidden", "always_visible"]


class ChannelSummaryResponse(BaseModel):
    id: str
    source_id: str
    source_name: str | None
    original_name: str
    normalized_name: str | None
    normalized_group: str | None
    content_type: ContentType
    inferred_country: str | None
    inferred_language: str | None
    inferred_category: str | None
    claimed_quality: str | None
    visibility_status: str
    protected_from_auto_merge: bool
    duplicate_cluster_id: str | None
    url_checksum: str | None
    original_tvg_id: str | None
    original_tvg_name: str | None
    original_logo_url: str | None
    line_number: int | None
    normalized_at: datetime | None
    explanations: list[dict[str, str]]
    filtering_reasons: list[dict[str, object]]


class ChannelListResponse(BaseModel):
    items: list[ChannelSummaryResponse]
    next_cursor: str | None
    total_count: int
    page_size: int


class ChannelGroupResponse(BaseModel):
    id: str
    name: str
    normalized_name: str
    sort_order: int
    is_visible: bool


class ChannelGroupListResponse(BaseModel):
    groups: list[ChannelGroupResponse]


class ChannelUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=260)
    group_name: str | None = Field(default=None, min_length=1, max_length=220)
    visibility_status: VisibilityStatus | None = None
    protected_from_auto_merge: bool | None = None


class ChannelSourceCandidateResponse(BaseModel):
    id: str
    raw_channel_id: str
    curated_channel_id: str
    role: str
    rank: int
    selection_reason: str | None
    original_name: str
    normalized_name: str | None
    normalized_group: str | None
    content_type: ContentType
    claimed_quality: str | None
    url_checksum: str | None
    attributes: dict[str, object]


class ChannelSourceCandidateListResponse(BaseModel):
    candidates: list[ChannelSourceCandidateResponse]


class NormalizationJobCreateRequest(BaseModel):
    source_id: str | None = None
    profile: FilterProfile = "recommended"
    process_now: bool = False


class NormalizationJobResponse(BaseModel):
    id: str
    source_id: str | None
    status: JobStatus
    profile: FilterProfile
    progress_percent: int
    message: str
    total_raw_channels: int
    processed_raw_channels: int
    started_at: datetime | None
    completed_at: datetime | None
    canceled_at: datetime | None
    failure_reason: str | None
    stats: dict[str, object]


class CleanupQueueResponse(BaseModel):
    key: str
    label: str
    count: int
    description: str


class CleanupQueuesResponse(BaseModel):
    queues: list[CleanupQueueResponse]


class CleanupProfileRequest(BaseModel):
    profile: FilterProfile = "recommended"
    source_id: str | None = None


class CleanupPreviewResponse(BaseModel):
    profile: FilterProfile
    source_id: str | None
    total_channels: int
    would_hide: int
    would_allow: int
    protected_count: int
    sample_channel_ids: list[str]
    reasons: dict[str, int]


class CleanupApplyResponse(CleanupPreviewResponse):
    applied: bool


class DuplicateClusterResponse(BaseModel):
    id: str
    label: str
    confidence_score: float
    review_status: str
    candidate_count: int
    primary_raw_channel_id: str | None
    explanations: list[dict[str, object]]


class DuplicateClusterListResponse(BaseModel):
    clusters: list[DuplicateClusterResponse]


class DuplicateActionResponse(BaseModel):
    cluster: DuplicateClusterResponse
    message: str


class ProtectionSummaryResponse(BaseModel):
    protected_channel_count: int
    protected_cluster_count: int
    total_protection_count: int


class ClearProtectionsResponse(ProtectionSummaryResponse):
    message: str
