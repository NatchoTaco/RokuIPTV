from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from streamforge_api.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class IdMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email", unique=True),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Session(IdMixin, TimestampMixin, Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_token_hash", "session_token_hash", unique=True),
        Index("ix_sessions_expires_at", "expires_at"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(64))


class Profile(IdMixin, TimestampMixin, Base):
    __tablename__ = "profiles"
    __table_args__ = (Index("ix_profiles_name", "name"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parental_controls_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Device(IdMixin, TimestampMixin, Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_profile_id", "profile_id"),
        Index("ix_devices_device_token_hash", "device_token_hash", unique=True),
    )

    profile_id: Mapped[str | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    room: Mapped[str | None] = mapped_column(String(120))
    platform: Mapped[str] = mapped_column(String(80), default="roku", nullable=False)
    device_token_hash: Mapped[str | None] = mapped_column(String(128))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DevicePairingCode(IdMixin, TimestampMixin, Base):
    __tablename__ = "device_pairing_codes"
    __table_args__ = (
        Index("ix_device_pairing_codes_code_hash", "code_hash", unique=True),
        Index("ix_device_pairing_codes_expires_at", "expires_at"),
    )

    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    device_request_id: Mapped[str] = mapped_column(String(120), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"))


class Source(IdMixin, TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        Index("ix_sources_status", "status"),
        Index("ix_sources_next_refresh_at", "next_refresh_at"),
        Index("ix_sources_deleted_at", "deleted_at"),
    )

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="pending", nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    secret_config_encrypted: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    refresh_interval_minutes: Mapped[int | None] = mapped_column(Integer)
    next_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_import_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failed_import_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    source_version: Mapped[str | None] = mapped_column(String(120))
    checksum: Mapped[str | None] = mapped_column(String(64))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlaylistImportJob(IdMixin, TimestampMixin, Base):
    __tablename__ = "playlist_import_jobs"
    __table_args__ = (
        Index("ix_playlist_import_jobs_source_id", "source_id"),
        Index("ix_playlist_import_jobs_status", "status"),
        Index("ix_playlist_import_jobs_created_at", "created_at"),
    )

    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    triggered_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    playlist_import_id: Mapped[str | None] = mapped_column(
        ForeignKey("playlist_imports.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(80), default="queued", nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="Queued for import.", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    worker_id: Mapped[str | None] = mapped_column(String(120))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)


class NormalizationJob(IdMixin, TimestampMixin, Base):
    __tablename__ = "normalization_jobs"
    __table_args__ = (
        Index("ix_normalization_jobs_source_id", "source_id"),
        Index("ix_normalization_jobs_status", "status"),
        Index("ix_normalization_jobs_created_at", "created_at"),
    )

    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(80), default="queued", nullable=False)
    profile: Mapped[str] = mapped_column(String(80), default="recommended", nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="Queued for normalization.", nullable=False)
    total_raw_channels: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_raw_channels: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    worker_id: Mapped[str | None] = mapped_column(String(120))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    stats_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class PlaylistImport(IdMixin, TimestampMixin, Base):
    __tablename__ = "playlist_imports"
    __table_args__ = (
        Index("ix_playlist_imports_source_id", "source_id"),
        Index("ix_playlist_imports_status", "status"),
        Index("ix_playlist_imports_started_at", "started_at"),
    )

    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    triggered_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    source_kind: Mapped[str] = mapped_column(String(80), default="m3u_url", nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="pending", nullable=False)
    channel_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    group_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    failures_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64))
    source_version: Mapped[str | None] = mapped_column(String(120))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)


class SourceStatus(IdMixin, TimestampMixin, Base):
    __tablename__ = "source_statuses"
    __table_args__ = (
        Index("ix_source_statuses_source_id", "source_id", unique=True),
        Index("ix_source_statuses_status", "status"),
        Index("ix_source_statuses_last_checked_at", "last_checked_at"),
    )

    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="pending", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="Source has not been imported yet.", nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_import_id: Mapped[str | None] = mapped_column(ForeignKey("playlist_imports.id", ondelete="SET NULL"))
    last_job_id: Mapped[str | None] = mapped_column(ForeignKey("playlist_import_jobs.id", ondelete="SET NULL"))
    channel_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    group_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ChannelGroup(IdMixin, TimestampMixin, Base):
    __tablename__ = "channel_groups"
    __table_args__ = (Index("ix_channel_groups_normalized_name", "normalized_name", unique=True),)

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(180), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DuplicateCluster(IdMixin, TimestampMixin, Base):
    __tablename__ = "duplicate_clusters"
    __table_args__ = (
        Index("ix_duplicate_clusters_confidence", "confidence_score"),
        Index("ix_duplicate_clusters_review_status", "review_status"),
    )

    label: Mapped[str] = mapped_column(String(220), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    review_status: Mapped[str] = mapped_column(String(80), default="pending", nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    primary_raw_channel_id: Mapped[str | None] = mapped_column(String(36))
    explanation_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    stats_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class RawChannel(IdMixin, TimestampMixin, Base):
    __tablename__ = "raw_channels"
    __table_args__ = (
        Index("ix_raw_channels_source_id", "source_id"),
        Index("ix_raw_channels_normalized_name", "normalized_name"),
        Index("ix_raw_channels_normalized_key", "normalized_key"),
        Index("ix_raw_channels_normalized_group", "normalized_group"),
        Index("ix_raw_channels_content_type", "content_type"),
        Index("ix_raw_channels_inferred_country", "inferred_country"),
        Index("ix_raw_channels_inferred_language", "inferred_language"),
        Index("ix_raw_channels_inferred_category", "inferred_category"),
        Index("ix_raw_channels_claimed_quality", "claimed_quality"),
        Index("ix_raw_channels_visibility_status", "visibility_status"),
        Index("ix_raw_channels_health_status", "health_status"),
        Index("ix_raw_channels_duplicate_cluster_id", "duplicate_cluster_id"),
        Index("ix_raw_channels_normalization_job_id", "normalization_job_id"),
    )

    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    playlist_import_id: Mapped[str | None] = mapped_column(
        ForeignKey("playlist_imports.id", ondelete="SET NULL")
    )
    duplicate_cluster_id: Mapped[str | None] = mapped_column(
        ForeignKey("duplicate_clusters.id", ondelete="SET NULL")
    )
    normalization_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("normalization_jobs.id", ondelete="SET NULL")
    )
    original_name: Mapped[str] = mapped_column(String(260), nullable=False)
    original_group: Mapped[str | None] = mapped_column(String(220))
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    original_tvg_id: Mapped[str | None] = mapped_column(String(220))
    original_tvg_name: Mapped[str | None] = mapped_column(String(260))
    original_logo_url: Mapped[str | None] = mapped_column(Text)
    source_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer)
    raw_extinf: Mapped[str | None] = mapped_column(Text)
    raw_attributes_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    url_checksum: Mapped[str | None] = mapped_column(String(64))
    normalized_name: Mapped[str | None] = mapped_column(String(260))
    normalized_key: Mapped[str | None] = mapped_column(String(260))
    normalized_group: Mapped[str | None] = mapped_column(String(220))
    content_type: Mapped[str] = mapped_column(String(80), default="unknown", nullable=False)
    inferred_country: Mapped[str | None] = mapped_column(String(80))
    inferred_language: Mapped[str | None] = mapped_column(String(80))
    inferred_category: Mapped[str | None] = mapped_column(String(120))
    claimed_quality: Mapped[str | None] = mapped_column(String(80))
    normalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    normalization_explanations_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    manual_display_name: Mapped[str | None] = mapped_column(String(260))
    manual_group_name: Mapped[str | None] = mapped_column(String(220))
    manual_visibility_status: Mapped[str | None] = mapped_column(String(80))
    protected_from_auto_merge: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    measured_resolution: Mapped[str | None] = mapped_column(String(80))
    measured_frame_rate: Mapped[float | None] = mapped_column(Float)
    codec_information_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    epg_status: Mapped[str] = mapped_column(String(80), default="unknown", nullable=False)
    health_status: Mapped[str] = mapped_column(String(80), default="unknown", nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float)
    reliability_score: Mapped[float | None] = mapped_column(Float)
    visibility_status: Mapped[str] = mapped_column(String(80), default="visible", nullable=False)
    filtering_explanations_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )


class CuratedChannel(IdMixin, TimestampMixin, Base):
    __tablename__ = "curated_channels"
    __table_args__ = (
        Index("ix_curated_channels_group_id", "group_id"),
        Index("ix_curated_channels_normalized_name", "normalized_name"),
        Index("ix_curated_channels_visibility_status", "visibility_status"),
    )

    group_id: Mapped[str | None] = mapped_column(ForeignKey("channel_groups.id", ondelete="SET NULL"))
    duplicate_cluster_id: Mapped[str | None] = mapped_column(
        ForeignKey("duplicate_clusters.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(260), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(260), nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), default="live_tv", nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    visibility_status: Mapped[str] = mapped_column(String(80), default="visible", nullable=False)
    source_candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ChannelSourceCandidate(IdMixin, TimestampMixin, Base):
    __tablename__ = "channel_source_candidates"
    __table_args__ = (
        Index("ix_channel_source_candidates_curated_channel_id", "curated_channel_id"),
        Index("ix_channel_source_candidates_raw_channel_id", "raw_channel_id"),
        Index("ix_channel_source_candidates_rank", "rank"),
        UniqueConstraint("raw_channel_id", name="uq_channel_source_candidates_raw_channel"),
    )

    curated_channel_id: Mapped[str] = mapped_column(
        ForeignKey("curated_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_channel_id: Mapped[str] = mapped_column(
        ForeignKey("raw_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(80), default="backup", nullable=False)
    rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    selection_reason: Mapped[str | None] = mapped_column(Text)


class ChannelAlias(IdMixin, TimestampMixin, Base):
    __tablename__ = "channel_aliases"
    __table_args__ = (Index("ix_channel_aliases_alias", "alias"),)

    curated_channel_id: Mapped[str] = mapped_column(
        ForeignKey("curated_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(260), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(260), nullable=False)


class EpgSource(IdMixin, TimestampMixin, Base):
    __tablename__ = "epg_sources"
    __table_args__ = (Index("ix_epg_sources_status", "status"),)

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="pending", nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EpgChannel(IdMixin, TimestampMixin, Base):
    __tablename__ = "epg_channels"
    __table_args__ = (
        Index("ix_epg_channels_epg_source_id", "epg_source_id"),
        Index("ix_epg_channels_external_id", "external_id"),
    )

    epg_source_id: Mapped[str] = mapped_column(
        ForeignKey("epg_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(260), nullable=False)
    display_name: Mapped[str] = mapped_column(String(260), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(80))


class Program(IdMixin, TimestampMixin, Base):
    __tablename__ = "programs"
    __table_args__ = (
        Index("ix_programs_epg_channel_time", "epg_channel_id", "starts_at", "ends_at"),
        Index("ix_programs_time_range", "starts_at", "ends_at"),
    )

    epg_channel_id: Mapped[str] = mapped_column(
        ForeignKey("epg_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ChannelEpgMapping(IdMixin, TimestampMixin, Base):
    __tablename__ = "channel_epg_mappings"
    __table_args__ = (
        UniqueConstraint("curated_channel_id", "epg_channel_id", name="uq_channel_epg_mapping"),
        Index("ix_channel_epg_mappings_curated_channel_id", "curated_channel_id"),
    )

    curated_channel_id: Mapped[str] = mapped_column(
        ForeignKey("curated_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    epg_channel_id: Mapped[str] = mapped_column(
        ForeignKey("epg_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class FilterRule(IdMixin, TimestampMixin, Base):
    __tablename__ = "filter_rules"
    __table_args__ = (
        Index("ix_filter_rules_rule_type", "rule_type"),
        Index("ix_filter_rules_action", "action"),
        Index("ix_filter_rules_priority", "priority"),
    )

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criteria_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class FilterDecision(IdMixin, TimestampMixin, Base):
    __tablename__ = "filter_decisions"
    __table_args__ = (
        Index("ix_filter_decisions_raw_channel_id", "raw_channel_id"),
        Index("ix_filter_decisions_action", "action"),
        Index("ix_filter_decisions_filter_rule_id", "filter_rule_id"),
    )

    raw_channel_id: Mapped[str] = mapped_column(
        ForeignKey("raw_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    filter_rule_id: Mapped[str | None] = mapped_column(
        ForeignKey("filter_rules.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    reasons_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_automatic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class StreamHealthResult(IdMixin, TimestampMixin, Base):
    __tablename__ = "stream_health_results"
    __table_args__ = (
        Index("ix_stream_health_results_raw_channel_id", "raw_channel_id"),
        Index("ix_stream_health_results_health_status", "health_status"),
        Index("ix_stream_health_results_checked_at", "checked_at"),
    )

    raw_channel_id: Mapped[str] = mapped_column(
        ForeignKey("raw_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    health_status: Mapped[str] = mapped_column(String(80), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    time_to_first_media_ms: Mapped[int | None] = mapped_column(Integer)
    video_codec: Mapped[str | None] = mapped_column(String(80))
    audio_codec: Mapped[str | None] = mapped_column(String(80))
    resolution: Mapped[str | None] = mapped_column(String(80))
    frame_rate: Mapped[float | None] = mapped_column(Float)
    bitrate: Mapped[int | None] = mapped_column(Integer)
    probe_duration_ms: Mapped[int | None] = mapped_column(Integer)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    raw_result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Favorite(IdMixin, TimestampMixin, Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("profile_id", "curated_channel_id", name="uq_profile_favorite_channel"),
        Index("ix_favorites_profile_id", "profile_id"),
    )

    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    curated_channel_id: Mapped[str] = mapped_column(
        ForeignKey("curated_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PlaybackProgress(IdMixin, TimestampMixin, Base):
    __tablename__ = "playback_progress"
    __table_args__ = (
        Index("ix_playback_progress_profile_channel", "profile_id", "curated_channel_id"),
        Index("ix_playback_progress_recording_id", "recording_id"),
    )

    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    curated_channel_id: Mapped[str | None] = mapped_column(
        ForeignKey("curated_channels.id", ondelete="CASCADE")
    )
    recording_id: Mapped[str | None] = mapped_column(ForeignKey("recordings.id", ondelete="CASCADE"))
    position_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Recording(IdMixin, TimestampMixin, Base):
    __tablename__ = "recordings"
    __table_args__ = (
        Index("ix_recordings_profile_id", "profile_id"),
        Index("ix_recordings_status", "status"),
        Index("ix_recordings_schedule", "starts_at", "ends_at"),
    )

    profile_id: Mapped[str | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))
    curated_channel_id: Mapped[str | None] = mapped_column(
        ForeignKey("curated_channels.id", ondelete="SET NULL")
    )
    program_id: Mapped[str | None] = mapped_column(ForeignKey("programs.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="scheduled", nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    padding_before_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    padding_after_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class RecordingRule(IdMixin, TimestampMixin, Base):
    __tablename__ = "recording_rules"
    __table_args__ = (
        Index("ix_recording_rules_profile_id", "profile_id"),
        Index("ix_recording_rules_status", "status"),
    )

    profile_id: Mapped[str | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="active", nullable=False)
    criteria_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    padding_before_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    padding_after_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class RecordingJob(IdMixin, TimestampMixin, Base):
    __tablename__ = "recording_jobs"
    __table_args__ = (
        Index("ix_recording_jobs_recording_id", "recording_id"),
        Index("ix_recording_jobs_status", "status"),
        Index("ix_recording_jobs_started_at", "started_at"),
    )

    recording_id: Mapped[str] = mapped_column(
        ForeignKey("recordings.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(80), default="pending", nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)


class RecordingConflict(IdMixin, TimestampMixin, Base):
    __tablename__ = "recording_conflicts"
    __table_args__ = (Index("ix_recording_conflicts_recording_id", "recording_id"),)

    recording_id: Mapped[str] = mapped_column(
        ForeignKey("recordings.id", ondelete="CASCADE"),
        nullable=False,
    )
    conflicting_recording_id: Mapped[str | None] = mapped_column(
        ForeignKey("recordings.id", ondelete="SET NULL")
    )
    severity: Mapped[str] = mapped_column(String(80), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecordingFile(IdMixin, TimestampMixin, Base):
    __tablename__ = "recording_files"
    __table_args__ = (Index("ix_recording_files_recording_id", "recording_id"),)

    recording_id: Mapped[str] = mapped_column(
        ForeignKey("recordings.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_location_id: Mapped[str | None] = mapped_column(
        ForeignKey("storage_locations.id", ondelete="SET NULL")
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(160))


class RetentionPolicy(IdMixin, TimestampMixin, Base):
    __tablename__ = "retention_policies"
    __table_args__ = (Index("ix_retention_policies_name", "name", unique=True),)

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    keep_count: Mapped[int | None] = mapped_column(Integer)
    keep_days: Mapped[int | None] = mapped_column(Integer)
    storage_quota_bytes: Mapped[int | None] = mapped_column(Integer)
    rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class StorageLocation(IdMixin, TimestampMixin, Base):
    __tablename__ = "storage_locations"
    __table_args__ = (Index("ix_storage_locations_purpose", "purpose"),)

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    purpose: Mapped[str] = mapped_column(String(80), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quota_bytes: Mapped[int | None] = mapped_column(Integer)
    last_validation_status: Mapped[str] = mapped_column(String(80), default="unknown", nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SystemSetting(IdMixin, TimestampMixin, Base):
    __tablename__ = "system_settings"
    __table_args__ = (Index("ix_system_settings_key", "key", unique=True),)

    key: Mapped[str] = mapped_column(String(180), nullable=False)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AuditEvent(IdMixin, TimestampMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_actor_user_id", "actor_user_id"),
        Index("ix_audit_events_event_type", "event_type"),
        Index("ix_audit_events_created_at", "created_at"),
    )

    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(160), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class SetupState(IdMixin, TimestampMixin, Base):
    __tablename__ = "setup_state"

    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_step: Mapped[str] = mapped_column(String(120), default="account", nullable=False)
    completed_steps_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    installation_mode: Mapped[str | None] = mapped_column(String(80))
