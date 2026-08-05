"""channel normalization and cleanup

Revision ID: 0003_channel_normalization
Revises: 0002_sources_ingestion
Create Date: 2026-08-05 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_channel_normalization"
down_revision: str | None = "0002_sources_ingestion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def id_column() -> sa.Column[str]:
    return sa.Column("id", sa.String(length=36), primary_key=True)


def timestamps() -> list[sa.Column[str]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "normalization_jobs",
        id_column(),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sources.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="queued"),
        sa.Column("profile", sa.String(length=80), nullable=False, server_default="recommended"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=False, server_default="Queued for normalization."),
        sa.Column("total_raw_channels", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_raw_channels", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("worker_id", sa.String(length=120)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("canceled_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("stats_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *timestamps(),
    )
    op.create_index("ix_normalization_jobs_source_id", "normalization_jobs", ["source_id"])
    op.create_index("ix_normalization_jobs_status", "normalization_jobs", ["status"])
    op.create_index("ix_normalization_jobs_created_at", "normalization_jobs", ["created_at"])

    op.add_column("duplicate_clusters", sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("duplicate_clusters", sa.Column("primary_raw_channel_id", sa.String(length=36)))
    op.add_column("duplicate_clusters", sa.Column("stats_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.create_index("ix_duplicate_clusters_review_status", "duplicate_clusters", ["review_status"])

    op.add_column(
        "raw_channels",
        sa.Column("normalization_job_id", sa.String(length=36), sa.ForeignKey("normalization_jobs.id", ondelete="SET NULL")),
    )
    op.add_column("raw_channels", sa.Column("normalized_key", sa.String(length=260)))
    op.add_column("raw_channels", sa.Column("content_type", sa.String(length=80), nullable=False, server_default="unknown"))
    op.add_column("raw_channels", sa.Column("normalized_at", sa.DateTime(timezone=True)))
    op.add_column(
        "raw_channels",
        sa.Column("normalization_explanations_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column("raw_channels", sa.Column("manual_display_name", sa.String(length=260)))
    op.add_column("raw_channels", sa.Column("manual_group_name", sa.String(length=220)))
    op.add_column("raw_channels", sa.Column("manual_visibility_status", sa.String(length=80)))
    op.add_column(
        "raw_channels",
        sa.Column("protected_from_auto_merge", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_raw_channels_normalized_key", "raw_channels", ["normalized_key"])
    op.create_index("ix_raw_channels_content_type", "raw_channels", ["content_type"])
    op.create_index("ix_raw_channels_inferred_country", "raw_channels", ["inferred_country"])
    op.create_index("ix_raw_channels_inferred_language", "raw_channels", ["inferred_language"])
    op.create_index("ix_raw_channels_inferred_category", "raw_channels", ["inferred_category"])
    op.create_index("ix_raw_channels_claimed_quality", "raw_channels", ["claimed_quality"])
    op.create_index("ix_raw_channels_normalization_job_id", "raw_channels", ["normalization_job_id"])

    op.add_column("curated_channels", sa.Column("content_type", sa.String(length=80), nullable=False, server_default="live_tv"))
    op.add_column("curated_channels", sa.Column("source_candidate_count", sa.Integer(), nullable=False, server_default="0"))

    op.create_unique_constraint(
        "uq_channel_source_candidates_raw_channel",
        "channel_source_candidates",
        ["raw_channel_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_channel_source_candidates_raw_channel",
        "channel_source_candidates",
        type_="unique",
    )

    op.drop_column("curated_channels", "source_candidate_count")
    op.drop_column("curated_channels", "content_type")

    op.drop_index("ix_raw_channels_normalization_job_id", table_name="raw_channels")
    op.drop_index("ix_raw_channels_claimed_quality", table_name="raw_channels")
    op.drop_index("ix_raw_channels_inferred_category", table_name="raw_channels")
    op.drop_index("ix_raw_channels_inferred_language", table_name="raw_channels")
    op.drop_index("ix_raw_channels_inferred_country", table_name="raw_channels")
    op.drop_index("ix_raw_channels_content_type", table_name="raw_channels")
    op.drop_index("ix_raw_channels_normalized_key", table_name="raw_channels")
    for column_name in (
        "protected_from_auto_merge",
        "manual_visibility_status",
        "manual_group_name",
        "manual_display_name",
        "normalization_explanations_json",
        "normalized_at",
        "content_type",
        "normalized_key",
        "normalization_job_id",
    ):
        op.drop_column("raw_channels", column_name)

    op.drop_index("ix_duplicate_clusters_review_status", table_name="duplicate_clusters")
    op.drop_column("duplicate_clusters", "stats_json")
    op.drop_column("duplicate_clusters", "primary_raw_channel_id")
    op.drop_column("duplicate_clusters", "candidate_count")

    op.drop_index("ix_normalization_jobs_created_at", table_name="normalization_jobs")
    op.drop_index("ix_normalization_jobs_status", table_name="normalization_jobs")
    op.drop_index("ix_normalization_jobs_source_id", table_name="normalization_jobs")
    op.drop_table("normalization_jobs")
