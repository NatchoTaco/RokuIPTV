"""runnable foundation

Revision ID: 0001_runnable_foundation
Revises:
Create Date: 2026-08-04 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_runnable_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def id_column() -> sa.Column[str]:
    return sa.Column("id", sa.String(length=36), primary_key=True)


def timestamps() -> list[sa.Column[str]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        id_column(),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "profiles",
        id_column(),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("parental_controls_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *timestamps(),
    )
    op.create_index("ix_profiles_name", "profiles", ["name"])

    op.create_table(
        "sources",
        id_column(),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="pending"),
        sa.Column("config_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_refresh_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index("ix_sources_status", "sources", ["status"])

    op.create_table(
        "channel_groups",
        id_column(),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("normalized_name", sa.String(length=180), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
    )
    op.create_index("ix_channel_groups_normalized_name", "channel_groups", ["normalized_name"], unique=True)

    op.create_table(
        "duplicate_clusters",
        id_column(),
        sa.Column("label", sa.String(length=220), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("review_status", sa.String(length=80), nullable=False, server_default="pending"),
        sa.Column("explanation_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        *timestamps(),
    )
    op.create_index("ix_duplicate_clusters_confidence", "duplicate_clusters", ["confidence_score"])

    op.create_table(
        "epg_sources",
        id_column(),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="pending"),
        sa.Column("config_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_refresh_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index("ix_epg_sources_status", "epg_sources", ["status"])

    op.create_table(
        "storage_locations",
        id_column(),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("purpose", sa.String(length=80), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("quota_bytes", sa.Integer()),
        sa.Column("last_validation_status", sa.String(length=80), nullable=False, server_default="unknown"),
        sa.Column("last_validated_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index("ix_storage_locations_purpose", "storage_locations", ["purpose"])

    op.create_table(
        "system_settings",
        id_column(),
        sa.Column("key", sa.String(length=180), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default=sa.false()),
        *timestamps(),
    )
    op.create_index("ix_system_settings_key", "system_settings", ["key"], unique=True)

    op.create_table(
        "setup_state",
        id_column(),
        sa.Column("is_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("current_step", sa.String(length=120), nullable=False, server_default="account"),
        sa.Column("completed_steps_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("installation_mode", sa.String(length=80)),
        *timestamps(),
    )

    op.create_table(
        "sessions",
        id_column(),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("ip_address", sa.String(length=64)),
        *timestamps(),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_token_hash", "sessions", ["session_token_hash"], unique=True)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])

    op.create_table(
        "devices",
        id_column(),
        sa.Column("profile_id", sa.String(length=36), sa.ForeignKey("profiles.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("room", sa.String(length=120)),
        sa.Column("platform", sa.String(length=80), nullable=False, server_default="roku"),
        sa.Column("device_token_hash", sa.String(length=128)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index("ix_devices_profile_id", "devices", ["profile_id"])
    op.create_index("ix_devices_device_token_hash", "devices", ["device_token_hash"], unique=True)

    op.create_table(
        "device_pairing_codes",
        id_column(),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("device_request_id", sa.String(length=120), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("device_id", sa.String(length=36), sa.ForeignKey("devices.id", ondelete="SET NULL")),
        *timestamps(),
    )
    op.create_index("ix_device_pairing_codes_code_hash", "device_pairing_codes", ["code_hash"], unique=True)
    op.create_index("ix_device_pairing_codes_expires_at", "device_pairing_codes", ["expires_at"])

    op.create_table(
        "playlist_imports",
        id_column(),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="pending"),
        sa.Column("channel_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.Text()),
        *timestamps(),
    )
    op.create_index("ix_playlist_imports_source_id", "playlist_imports", ["source_id"])
    op.create_index("ix_playlist_imports_status", "playlist_imports", ["status"])

    op.create_table(
        "raw_channels",
        id_column(),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("playlist_import_id", sa.String(length=36), sa.ForeignKey("playlist_imports.id", ondelete="SET NULL")),
        sa.Column("duplicate_cluster_id", sa.String(length=36), sa.ForeignKey("duplicate_clusters.id", ondelete="SET NULL")),
        sa.Column("original_name", sa.String(length=260), nullable=False),
        sa.Column("original_group", sa.String(length=220)),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("original_tvg_id", sa.String(length=220)),
        sa.Column("original_tvg_name", sa.String(length=260)),
        sa.Column("original_logo_url", sa.Text()),
        sa.Column("source_metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("normalized_name", sa.String(length=260)),
        sa.Column("normalized_group", sa.String(length=220)),
        sa.Column("inferred_country", sa.String(length=80)),
        sa.Column("inferred_language", sa.String(length=80)),
        sa.Column("inferred_category", sa.String(length=120)),
        sa.Column("claimed_quality", sa.String(length=80)),
        sa.Column("measured_resolution", sa.String(length=80)),
        sa.Column("measured_frame_rate", sa.Float()),
        sa.Column("codec_information_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("epg_status", sa.String(length=80), nullable=False, server_default="unknown"),
        sa.Column("health_status", sa.String(length=80), nullable=False, server_default="unknown"),
        sa.Column("quality_score", sa.Float()),
        sa.Column("reliability_score", sa.Float()),
        sa.Column("visibility_status", sa.String(length=80), nullable=False, server_default="visible"),
        sa.Column("filtering_explanations_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        *timestamps(),
    )
    op.create_index("ix_raw_channels_source_id", "raw_channels", ["source_id"])
    op.create_index("ix_raw_channels_normalized_name", "raw_channels", ["normalized_name"])
    op.create_index("ix_raw_channels_normalized_group", "raw_channels", ["normalized_group"])
    op.create_index("ix_raw_channels_visibility_status", "raw_channels", ["visibility_status"])
    op.create_index("ix_raw_channels_health_status", "raw_channels", ["health_status"])
    op.create_index("ix_raw_channels_duplicate_cluster_id", "raw_channels", ["duplicate_cluster_id"])

    op.create_table(
        "curated_channels",
        id_column(),
        sa.Column("group_id", sa.String(length=36), sa.ForeignKey("channel_groups.id", ondelete="SET NULL")),
        sa.Column("duplicate_cluster_id", sa.String(length=36), sa.ForeignKey("duplicate_clusters.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(length=260), nullable=False),
        sa.Column("normalized_name", sa.String(length=260), nullable=False),
        sa.Column("logo_url", sa.Text()),
        sa.Column("visibility_status", sa.String(length=80), nullable=False, server_default="visible"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *timestamps(),
    )
    op.create_index("ix_curated_channels_group_id", "curated_channels", ["group_id"])
    op.create_index("ix_curated_channels_normalized_name", "curated_channels", ["normalized_name"])
    op.create_index("ix_curated_channels_visibility_status", "curated_channels", ["visibility_status"])

    op.create_table(
        "channel_source_candidates",
        id_column(),
        sa.Column("curated_channel_id", sa.String(length=36), sa.ForeignKey("curated_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_channel_id", sa.String(length=36), sa.ForeignKey("raw_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False, server_default="backup"),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selection_reason", sa.Text()),
        *timestamps(),
    )
    op.create_index("ix_channel_source_candidates_curated_channel_id", "channel_source_candidates", ["curated_channel_id"])
    op.create_index("ix_channel_source_candidates_raw_channel_id", "channel_source_candidates", ["raw_channel_id"])
    op.create_index("ix_channel_source_candidates_rank", "channel_source_candidates", ["rank"])

    op.create_table(
        "channel_aliases",
        id_column(),
        sa.Column("curated_channel_id", sa.String(length=36), sa.ForeignKey("curated_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias", sa.String(length=260), nullable=False),
        sa.Column("normalized_alias", sa.String(length=260), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_channel_aliases_alias", "channel_aliases", ["alias"])

    op.create_table(
        "epg_channels",
        id_column(),
        sa.Column("epg_source_id", sa.String(length=36), sa.ForeignKey("epg_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(length=260), nullable=False),
        sa.Column("display_name", sa.String(length=260), nullable=False),
        sa.Column("icon_url", sa.Text()),
        sa.Column("language", sa.String(length=80)),
        *timestamps(),
    )
    op.create_index("ix_epg_channels_epg_source_id", "epg_channels", ["epg_source_id"])
    op.create_index("ix_epg_channels_external_id", "epg_channels", ["external_id"])

    op.create_table(
        "programs",
        id_column(),
        sa.Column("epg_channel_id", sa.String(length=36), sa.ForeignKey("epg_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("subtitle", sa.String(length=300)),
        sa.Column("description", sa.Text()),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *timestamps(),
    )
    op.create_index("ix_programs_epg_channel_time", "programs", ["epg_channel_id", "starts_at", "ends_at"])
    op.create_index("ix_programs_time_range", "programs", ["starts_at", "ends_at"])

    op.create_table(
        "channel_epg_mappings",
        id_column(),
        sa.Column("curated_channel_id", sa.String(length=36), sa.ForeignKey("curated_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("epg_channel_id", sa.String(length=36), sa.ForeignKey("epg_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
        *timestamps(),
        sa.UniqueConstraint("curated_channel_id", "epg_channel_id", name="uq_channel_epg_mapping"),
    )
    op.create_index("ix_channel_epg_mappings_curated_channel_id", "channel_epg_mappings", ["curated_channel_id"])

    op.create_table(
        "filter_rules",
        id_column(),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("rule_type", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criteria_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("explanation", sa.Text(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_filter_rules_rule_type", "filter_rules", ["rule_type"])
    op.create_index("ix_filter_rules_action", "filter_rules", ["action"])
    op.create_index("ix_filter_rules_priority", "filter_rules", ["priority"])

    op.create_table(
        "filter_decisions",
        id_column(),
        sa.Column("raw_channel_id", sa.String(length=36), sa.ForeignKey("raw_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filter_rule_id", sa.String(length=36), sa.ForeignKey("filter_rules.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("reasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("is_automatic", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
    )
    op.create_index("ix_filter_decisions_raw_channel_id", "filter_decisions", ["raw_channel_id"])
    op.create_index("ix_filter_decisions_action", "filter_decisions", ["action"])
    op.create_index("ix_filter_decisions_filter_rule_id", "filter_decisions", ["filter_rule_id"])

    op.create_table(
        "stream_health_results",
        id_column(),
        sa.Column("raw_channel_id", sa.String(length=36), sa.ForeignKey("raw_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("health_status", sa.String(length=80), nullable=False),
        sa.Column("http_status", sa.Integer()),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("time_to_first_media_ms", sa.Integer()),
        sa.Column("video_codec", sa.String(length=80)),
        sa.Column("audio_codec", sa.String(length=80)),
        sa.Column("resolution", sa.String(length=80)),
        sa.Column("frame_rate", sa.Float()),
        sa.Column("bitrate", sa.Integer()),
        sa.Column("probe_duration_ms", sa.Integer()),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("raw_result_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *timestamps(),
    )
    op.create_index("ix_stream_health_results_raw_channel_id", "stream_health_results", ["raw_channel_id"])
    op.create_index("ix_stream_health_results_health_status", "stream_health_results", ["health_status"])
    op.create_index("ix_stream_health_results_checked_at", "stream_health_results", ["checked_at"])

    op.create_table(
        "favorites",
        id_column(),
        sa.Column("profile_id", sa.String(length=36), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("curated_channel_id", sa.String(length=36), sa.ForeignKey("curated_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *timestamps(),
        sa.UniqueConstraint("profile_id", "curated_channel_id", name="uq_profile_favorite_channel"),
    )
    op.create_index("ix_favorites_profile_id", "favorites", ["profile_id"])

    op.create_table(
        "recordings",
        id_column(),
        sa.Column("profile_id", sa.String(length=36), sa.ForeignKey("profiles.id", ondelete="SET NULL")),
        sa.Column("curated_channel_id", sa.String(length=36), sa.ForeignKey("curated_channels.id", ondelete="SET NULL")),
        sa.Column("program_id", sa.String(length=36), sa.ForeignKey("programs.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="scheduled"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("padding_before_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("padding_after_seconds", sa.Integer(), nullable=False, server_default="0"),
        *timestamps(),
    )
    op.create_index("ix_recordings_profile_id", "recordings", ["profile_id"])
    op.create_index("ix_recordings_status", "recordings", ["status"])
    op.create_index("ix_recordings_schedule", "recordings", ["starts_at", "ends_at"])

    op.create_table(
        "playback_progress",
        id_column(),
        sa.Column("profile_id", sa.String(length=36), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("curated_channel_id", sa.String(length=36), sa.ForeignKey("curated_channels.id", ondelete="CASCADE")),
        sa.Column("recording_id", sa.String(length=36), sa.ForeignKey("recordings.id", ondelete="CASCADE")),
        sa.Column("position_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_played_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_playback_progress_profile_channel", "playback_progress", ["profile_id", "curated_channel_id"])
    op.create_index("ix_playback_progress_recording_id", "playback_progress", ["recording_id"])

    op.create_table(
        "recording_rules",
        id_column(),
        sa.Column("profile_id", sa.String(length=36), sa.ForeignKey("profiles.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("rule_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="active"),
        sa.Column("criteria_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("padding_before_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("padding_after_seconds", sa.Integer(), nullable=False, server_default="0"),
        *timestamps(),
    )
    op.create_index("ix_recording_rules_profile_id", "recording_rules", ["profile_id"])
    op.create_index("ix_recording_rules_status", "recording_rules", ["status"])

    op.create_table(
        "recording_jobs",
        id_column(),
        sa.Column("recording_id", sa.String(length=36), sa.ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="pending"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.Text()),
        *timestamps(),
    )
    op.create_index("ix_recording_jobs_recording_id", "recording_jobs", ["recording_id"])
    op.create_index("ix_recording_jobs_status", "recording_jobs", ["status"])
    op.create_index("ix_recording_jobs_started_at", "recording_jobs", ["started_at"])

    op.create_table(
        "recording_conflicts",
        id_column(),
        sa.Column("recording_id", sa.String(length=36), sa.ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conflicting_recording_id", sa.String(length=36), sa.ForeignKey("recordings.id", ondelete="SET NULL")),
        sa.Column("severity", sa.String(length=80), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index("ix_recording_conflicts_recording_id", "recording_conflicts", ["recording_id"])

    op.create_table(
        "recording_files",
        id_column(),
        sa.Column("recording_id", sa.String(length=36), sa.ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_location_id", sa.String(length=36), sa.ForeignKey("storage_locations.id", ondelete="SET NULL")),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("checksum", sa.String(length=160)),
        *timestamps(),
    )
    op.create_index("ix_recording_files_recording_id", "recording_files", ["recording_id"])

    op.create_table(
        "retention_policies",
        id_column(),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("keep_count", sa.Integer()),
        sa.Column("keep_days", sa.Integer()),
        sa.Column("storage_quota_bytes", sa.Integer()),
        sa.Column("rules_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *timestamps(),
    )
    op.create_index("ix_retention_policies_name", "retention_policies", ["name"], unique=True)

    op.create_table(
        "audit_events",
        id_column(),
        sa.Column("actor_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(length=160), nullable=False),
        sa.Column("ip_address", sa.String(length=64)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("details_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *timestamps(),
    )
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    for table_name in (
        "audit_events",
        "retention_policies",
        "recording_files",
        "recording_conflicts",
        "recording_jobs",
        "recording_rules",
        "playback_progress",
        "recordings",
        "favorites",
        "stream_health_results",
        "filter_decisions",
        "filter_rules",
        "channel_epg_mappings",
        "programs",
        "epg_channels",
        "channel_aliases",
        "channel_source_candidates",
        "curated_channels",
        "raw_channels",
        "playlist_imports",
        "device_pairing_codes",
        "devices",
        "sessions",
        "setup_state",
        "system_settings",
        "storage_locations",
        "epg_sources",
        "duplicate_clusters",
        "channel_groups",
        "sources",
        "profiles",
        "users",
    ):
        op.drop_table(table_name)
