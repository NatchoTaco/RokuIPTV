from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

SourceType = Literal["m3u_url", "m3u_upload", "demo_playlist"]
SourceState = Literal["healthy", "importing", "warning", "offline", "failed", "disabled", "pending"]
ImportJobState = Literal["queued", "running", "succeeded", "failed"]
PlaylistImportState = Literal["queued", "running", "completed", "warning", "failed"]


class SourceValidateUrlRequest(BaseModel):
    url: HttpUrl


class SourceValidationResponse(BaseModel):
    playlist_reachable: bool
    channel_count: int
    group_count: int
    estimated_import_time_seconds: int
    warnings: list[str]
    errors: list[str]
    checksum: str | None = None
    source_version: str | None = None


class SourceCreateUrlRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    url: HttpUrl
    refresh_interval_minutes: int | None = Field(default=1440, ge=15, le=43200)


class SourceCreateDemoRequest(BaseModel):
    name: str = Field(default="Synthetic Demonstration Playlist", min_length=1, max_length=180)
    refresh_interval_minutes: int | None = Field(default=None, ge=15, le=43200)


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
