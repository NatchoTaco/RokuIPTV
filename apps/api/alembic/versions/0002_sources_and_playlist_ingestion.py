"""sources and playlist ingestion

Revision ID: 0002_sources_ingestion
Revises: 0001_runnable_foundation
Create Date: 2026-08-04 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_sources_ingestion"
down_revision: str | None = "0001_runnable_foundation"
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
    op.add_column("sources", sa.Column("secret_config_encrypted", sa.Text()))
    op.add_column("sources", sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("sources", sa.Column("refresh_interval_minutes", sa.Integer()))
    op.add_column("sources", sa.Column("next_refresh_at", sa.DateTime(timezone=True)))
    op.add_column("sources", sa.Column("last_successful_import_at", sa.DateTime(timezone=True)))
    op.add_column("sources", sa.Column("last_failed_import_at", sa.DateTime(timezone=True)))
    op.add_column("sources", sa.Column("last_error", sa.Text()))
    op.add_column("sources", sa.Column("source_version", sa.String(length=120)))
    op.add_column("sources", sa.Column("checksum", sa.String(length=64)))
    op.add_column("sources", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.create_index("ix_sources_next_refresh_at", "sources", ["next_refresh_at"])
    op.create_index("ix_sources_deleted_at", "sources", ["deleted_at"])

    op.create_table(
        "playlist_import_jobs",
        id_column(),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("triggered_by_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("playlist_import_id", sa.String(length=36), sa.ForeignKey("playlist_imports.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="queued"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=False, server_default="Queued for import."),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("worker_id", sa.String(length=120)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.Text()),
        *timestamps(),
    )
    op.create_index("ix_playlist_import_jobs_source_id", "playlist_import_jobs", ["source_id"])
    op.create_index("ix_playlist_import_jobs_status", "playlist_import_jobs", ["status"])
    op.create_index("ix_playlist_import_jobs_created_at", "playlist_import_jobs", ["created_at"])

    op.add_column(
        "playlist_imports",
        sa.Column("triggered_by_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.add_column("playlist_imports", sa.Column("source_kind", sa.String(length=80), nullable=False, server_default="m3u_url"))
    op.add_column("playlist_imports", sa.Column("group_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("playlist_imports", sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("playlist_imports", sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("playlist_imports", sa.Column("warnings_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("playlist_imports", sa.Column("failures_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("playlist_imports", sa.Column("checksum", sa.String(length=64)))
    op.add_column("playlist_imports", sa.Column("source_version", sa.String(length=120)))
    op.add_column("playlist_imports", sa.Column("duration_ms", sa.Integer()))
    op.create_index("ix_playlist_imports_started_at", "playlist_imports", ["started_at"])

    op.create_table(
        "source_statuses",
        id_column(),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text(), nullable=False, server_default="Source has not been imported yet."),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.Column("last_import_id", sa.String(length=36), sa.ForeignKey("playlist_imports.id", ondelete="SET NULL")),
        sa.Column("last_job_id", sa.String(length=36), sa.ForeignKey("playlist_import_jobs.id", ondelete="SET NULL")),
        sa.Column("channel_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("group_count", sa.Integer(), nullable=False, server_default="0"),
        *timestamps(),
    )
    op.create_index("ix_source_statuses_source_id", "source_statuses", ["source_id"], unique=True)
    op.create_index("ix_source_statuses_status", "source_statuses", ["status"])
    op.create_index("ix_source_statuses_last_checked_at", "source_statuses", ["last_checked_at"])

    op.add_column("raw_channels", sa.Column("line_number", sa.Integer()))
    op.add_column("raw_channels", sa.Column("raw_extinf", sa.Text()))
    op.add_column("raw_channels", sa.Column("raw_attributes_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("raw_channels", sa.Column("url_checksum", sa.String(length=64)))


def downgrade() -> None:
    op.drop_column("raw_channels", "url_checksum")
    op.drop_column("raw_channels", "raw_attributes_json")
    op.drop_column("raw_channels", "raw_extinf")
    op.drop_column("raw_channels", "line_number")

    op.drop_table("source_statuses")

    op.drop_index("ix_playlist_imports_started_at", table_name="playlist_imports")
    for column_name in (
        "duration_ms",
        "source_version",
        "checksum",
        "failures_json",
        "warnings_json",
        "failure_count",
        "warning_count",
        "group_count",
        "source_kind",
        "triggered_by_user_id",
    ):
        op.drop_column("playlist_imports", column_name)

    op.drop_table("playlist_import_jobs")

    op.drop_index("ix_sources_deleted_at", table_name="sources")
    op.drop_index("ix_sources_next_refresh_at", table_name="sources")
    for column_name in (
        "deleted_at",
        "checksum",
        "source_version",
        "last_error",
        "last_failed_import_at",
        "last_successful_import_at",
        "next_refresh_at",
        "refresh_interval_minutes",
        "is_enabled",
        "secret_config_encrypted",
    ):
        op.drop_column("sources", column_name)
