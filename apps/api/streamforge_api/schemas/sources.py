from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["m3u_url", "m3u_upload", "demo_playlist"]
SourceState = Literal["healthy", "importing", "warning", "offline", "failed", "disabled", "pending"]
ContentType = Literal["live_tv", "movie", "series", "unknown"]
ImportJobState = Literal["queued", "running", "succeeded", "failed"]
PlaylistImportState = Literal["queued", "running", "completed", "warning", "failed"]


class SourceValidateUrlRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)
    enabled_content_types: list[ContentType] = Field(default_factory=lambda: ["live_tv"])


class SourceValidationResponse(BaseModel):
    playlist_reachable: bool
    channel_count: int
    total_entry_count: int = 0
    selected_entry_count: int = 0
    excluded_entry_count: int = 0
    group_count: int
    content_counts: dict[str, int] = Field(default_factory=dict)
    selected_content_types: list[ContentType] = Field(default_factory=lambda: ["live_tv"])
    deferred_content_types: list[ContentType] = Field(default_factory=list)
    estimated_import_time_seconds: int
    estimated_database_rows: int = 0
    estimated_database_bytes: int = 0
    requires_confirmation: bool = False
    confirmation_threshold_entries: int | None = None
    metadata_samples: list[dict[str, object]] = Field(default_factory=list)
    warnings: list[str]
    errors: list[str]
    checksum: str | None = None
    source_version: str | None = None


class SourceCreateUrlRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    url: str = Field(min_length=1, max_length=4096)
    refresh_interval_minutes: int | None = Field(default=1440, ge=15, le=43200)
    enabled_content_types: list[ContentType] = Field(default_factory=lambda: ["live_tv"])
    confirm_large_import: bool = False


class SourceCreateDemoRequest(BaseModel):
    name: str = Field(default="Synthetic Demonstration Playlist", min_length=1, max_length=180)
    refresh_interval_minutes: int | None = Field(default=None, ge=15, le=43200)
    enabled_content_types: list[ContentType] = Field(default_factory=lambda: ["live_tv"])
    confirm_large_import: bool = False


class SourceUpdateRequest(BaseModel):
    is_enabled: bool | None = None
    refresh_interval_minutes: int | None = Field(default=None, ge=15, le=43200)


class SourceStatusResponse(BaseModel):
    status: SourceState
    message: str
    last_checked_at: datetime | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    channel_count: int
    group_count: int


class PlaylistImportJobResponse(BaseModel):
    id: str
    source_id: str
    playlist_import_id: str | None
    status: ImportJobState
    progress_percent: int
    message: str
    started_at: datetime | None
    completed_at: datetime | None
    failure_reason: str | None


class SourceSummaryResponse(BaseModel):
    id: str
    name: str
    source_type: SourceType
    status: SourceState
    status_message: str
    display_location: str
    is_enabled: bool
    enabled_content_types: list[ContentType]
    refresh_interval_minutes: int | None
    last_updated_at: datetime
    last_refresh_at: datetime | None
    next_refresh_at: datetime | None
    last_error: str | None
    channel_count: int
    group_count: int
    active_job: PlaylistImportJobResponse | None


class SourceListResponse(BaseModel):
    sources: list[SourceSummaryResponse]


class SourceCreatedResponse(BaseModel):
    source: SourceSummaryResponse
    job: PlaylistImportJobResponse


class PlaylistImportHistoryItem(BaseModel):
    id: str
    source_id: str
    source_name: str
    source_kind: SourceType
    status: PlaylistImportState
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    channel_count: int
    group_count: int
    warning_count: int
    failure_count: int
    warnings: list[str]
    failures: list[str]
    failure_reason: str | None
    checksum: str | None
    source_version: str | None


class PlaylistImportHistoryResponse(BaseModel):
    imports: list[PlaylistImportHistoryItem]
