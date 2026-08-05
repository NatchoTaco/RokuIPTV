from __future__ import annotations

import base64
import json
import socket
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import cast

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from streamforge_api.core.config import Settings
from streamforge_api.core.errors import (
    ChannelNotFoundError,
    DuplicateClusterNotFoundError,
    NormalizationJobNotFoundError,
    SourceNotFoundError,
    SourceValidationError,
)
from streamforge_api.core.redaction import redact_payload, redact_text
from streamforge_api.domain.channel_normalization import (
    FilterProfile,
    NormalizationResult,
    STANDARD_GROUPS,
    automatic_filter_reasons,
    duplicate_confidence,
    evaluate_filter,
    normalize_channel,
    normalize_key,
)
from streamforge_api.models import (
    ChannelGroup,
    ChannelSourceCandidate,
    CuratedChannel,
    DuplicateCluster,
    FilterDecision,
    NormalizationJob,
    RawChannel,
    Source,
    utcnow,
)
from streamforge_api.schemas.channels import (
    ChannelGroupListResponse,
    ChannelGroupResponse,
    ChannelListResponse,
    ChannelSourceCandidateListResponse,
    ChannelSourceCandidateResponse,
    ChannelSummaryResponse,
    ChannelUpdateRequest,
    ClearProtectionsResponse,
    CleanupApplyResponse,
    CleanupPreviewResponse,
    CleanupQueueResponse,
    CleanupQueuesResponse,
    ContentType,
    DuplicateActionResponse,
    DuplicateClusterListResponse,
    DuplicateClusterResponse,
    JobStatus,
    NormalizationJobResponse,
    ProtectionSummaryResponse,
)

QUALITY_RANK: dict[str, int] = {
    "4K": 50,
    "UHD": 50,
    "FHD": 40,
    "HD": 30,
    "60 FPS": 25,
    "50 FPS": 24,
    "SD": 10,
}


@dataclass(frozen=True)
class CleanupPreview:
    total_channels: int
    would_hide: int
    would_allow: int
    protected_count: int
    sample_channel_ids: list[str]
    reasons: dict[str, int]


class ChannelService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def list_channels(
        self,
        *,
        cursor: str | None,
        page_size: int | None,
        search: str | None,
        source_id: str | None,
        group: str | None,
        visibility_status: str | None,
        content_type: str | None,
        duplicate_status: str | None,
    ) -> ChannelListResponse:
        limit = min(page_size or self.settings.channel_page_size_default, 500)
        offset = self._decode_cursor(cursor)
        filters = self._raw_channel_filters(source_id=source_id)
        if search:
            search_text = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(RawChannel.original_name).like(search_text),
                    func.lower(RawChannel.normalized_name).like(search_text),
                    func.lower(RawChannel.original_tvg_id).like(search_text),
                    func.lower(RawChannel.original_tvg_name).like(search_text),
                )
            )
        if group:
            filters.append(RawChannel.normalized_group == group)
        if visibility_status == "protected":
            filters.append(RawChannel.protected_from_auto_merge.is_(True))
        elif visibility_status:
            filters.append(RawChannel.visibility_status == visibility_status)
        if content_type:
            filters.append(RawChannel.content_type == content_type)
        if duplicate_status == "duplicates":
            filters.append(RawChannel.duplicate_cluster_id.is_not(None))
        elif duplicate_status == "unique":
            filters.append(RawChannel.duplicate_cluster_id.is_(None))

        total_count = self.db.scalar(select(func.count()).select_from(RawChannel).where(*filters)) or 0
        channels = self.db.scalars(
            select(RawChannel)
            .where(*filters)
            .order_by(
                RawChannel.normalized_group.asc(),
                RawChannel.normalized_name.asc(),
                RawChannel.original_name.asc(),
                RawChannel.id.asc(),
            )
            .offset(offset)
            .limit(limit + 1)
        ).all()
        visible_channels = channels[:limit]
        source_names = self._source_names({channel.source_id for channel in visible_channels})
        next_cursor = self._encode_cursor(offset + limit) if len(channels) > limit else None
        return ChannelListResponse(
            items=[self._channel_response(channel, source_names.get(channel.source_id)) for channel in visible_channels],
            next_cursor=next_cursor,
            total_count=total_count,
            page_size=limit,
        )

    def list_groups(self) -> ChannelGroupListResponse:
        groups = self.db.scalars(select(ChannelGroup).order_by(ChannelGroup.sort_order.asc(), ChannelGroup.name.asc())).all()
        return ChannelGroupListResponse(
            groups=[
                ChannelGroupResponse(
                    id=group.id,
                    name=group.name,
                    normalized_name=group.normalized_name,
                    sort_order=group.sort_order,
                    is_visible=group.is_visible,
                )
                for group in groups
            ]
        )

    def update_channel(self, raw_channel_id: str, payload: ChannelUpdateRequest) -> ChannelSummaryResponse:
        channel = self.db.get(RawChannel, raw_channel_id)
        if channel is None:
            raise ChannelNotFoundError()
        if payload.display_name is not None:
            channel.manual_display_name = payload.display_name.strip()
            channel.normalized_name = channel.manual_display_name
            channel.normalized_key = normalize_key(channel.manual_display_name)
        if payload.group_name is not None:
            channel.manual_group_name = payload.group_name.strip()
            channel.normalized_group = self._canonical_group_name(channel.manual_group_name)
            self._ensure_standard_groups()
        if payload.visibility_status is not None:
            channel.manual_visibility_status = payload.visibility_status
            channel.visibility_status = payload.visibility_status
            channel.filtering_explanations_json = [
                {
                    "rule": "manual_override",
                    "reason": f"Manual visibility set to {payload.visibility_status}.",
                }
            ]
        if payload.protected_from_auto_merge is not None:
            channel.protected_from_auto_merge = payload.protected_from_auto_merge
        channel.updated_at = utcnow()
        self.db.commit()
        return self._channel_response(channel, self._source_names({channel.source_id}).get(channel.source_id))

    def list_source_candidates(self, raw_channel_id: str) -> ChannelSourceCandidateListResponse:
        channel = self.db.get(RawChannel, raw_channel_id)
        if channel is None:
            raise ChannelNotFoundError()
        if channel.duplicate_cluster_id is None:
            candidates = self.db.execute(
                select(ChannelSourceCandidate, RawChannel)
                .join(RawChannel, RawChannel.id == ChannelSourceCandidate.raw_channel_id)
                .where(ChannelSourceCandidate.raw_channel_id == raw_channel_id)
                .order_by(ChannelSourceCandidate.rank.asc())
            ).all()
        else:
            candidates = self.db.execute(
                select(ChannelSourceCandidate, RawChannel)
                .join(RawChannel, RawChannel.id == ChannelSourceCandidate.raw_channel_id)
                .where(RawChannel.duplicate_cluster_id == channel.duplicate_cluster_id)
                .order_by(ChannelSourceCandidate.rank.asc())
            ).all()
        return ChannelSourceCandidateListResponse(
            candidates=[
                self._candidate_response(candidate, raw_channel)
                for candidate, raw_channel in candidates
            ]
        )

    def create_normalization_job(
        self,
        *,
        source_id: str | None,
        profile: FilterProfile,
        process_now: bool,
    ) -> NormalizationJobResponse:
        if source_id is not None and self.db.get(Source, source_id) is None:
            raise SourceNotFoundError()
        job = NormalizationJob(
            source_id=source_id,
            profile=profile,
            status="queued",
            progress_percent=0,
            message="Queued for channel normalization.",
        )
        self.db.add(job)
        self.db.commit()
        if process_now:
            return self.process_normalization_job(job.id)
        return self._job_response(job)

    def get_normalization_job(self, job_id: str) -> NormalizationJobResponse:
        job = self.db.get(NormalizationJob, job_id)
        if job is None:
            raise NormalizationJobNotFoundError()
        return self._job_response(job)

    def cancel_normalization_job(self, job_id: str) -> NormalizationJobResponse:
        job = self.db.get(NormalizationJob, job_id)
        if job is None:
            raise NormalizationJobNotFoundError()
        if job.status in {"queued", "running"}:
            job.status = "canceled"
            job.progress_percent = 100
            job.message = "Normalization job was canceled."
            job.canceled_at = utcnow()
            self.db.commit()
        return self._job_response(job)

    def process_next_queued_normalization_job(self, *, worker_id: str | None = None) -> bool:
        job = self.db.scalar(
            select(NormalizationJob)
            .where(NormalizationJob.status == "queued")
            .order_by(NormalizationJob.created_at.asc())
            .limit(1)
        )
        if job is None:
            return False
        job.worker_id = worker_id or socket.gethostname()
        self.db.commit()
        self.process_normalization_job(job.id)
        return True

    def process_normalization_job(self, job_id: str) -> NormalizationJobResponse:
        job = self.db.get(NormalizationJob, job_id)
        if job is None:
            raise NormalizationJobNotFoundError()
        if job.status == "canceled":
            return self._job_response(job)

        profile = cast(FilterProfile, job.profile)
        filters = self._raw_channel_filters(source_id=job.source_id)
        total = self.db.scalar(select(func.count()).select_from(RawChannel).where(*filters)) or 0
        now = utcnow()
        job.status = "running"
        job.started_at = now
        job.message = "Normalizing raw channels."
        job.total_raw_channels = total
        job.processed_raw_channels = 0
        job.progress_percent = 5
        self.db.commit()

        stats: Counter[str] = Counter()
        try:
            self._ensure_standard_groups()
            self._reset_generated_lineup(source_id=job.source_id)
            self._delete_automatic_filter_decisions(source_id=job.source_id)

            processed = 0
            last_id: str | None = None
            while True:
                job = self.db.get(NormalizationJob, job_id)
                if job is None:
                    raise NormalizationJobNotFoundError()
                if job.status == "canceled":
                    return self._job_response(job)
                batch_filters = list(filters)
                if last_id is not None:
                    batch_filters.append(RawChannel.id > last_id)
                channels = self.db.scalars(
                    select(RawChannel)
                    .where(*batch_filters)
                    .order_by(RawChannel.id.asc())
                    .limit(self.settings.channel_normalization_batch_size)
                ).all()
                if not channels:
                    break
                raw_updates: list[dict[str, object]] = []
                decision_rows: list[dict[str, object]] = []
                for channel in channels:
                    result = self._normalize_raw_channel(channel)
                    filtering = evaluate_filter(
                        result,
                        profile=profile,
                        manual_visibility_status=channel.manual_visibility_status,
                    )
                    display_name = channel.manual_display_name or result.display_name
                    group_name = self._canonical_group_name(channel.manual_group_name or result.group_name)
                    raw_updates.append(
                        {
                            "id": channel.id,
                            "updated_at": utcnow(),
                            "normalization_job_id": job_id,
                            "normalized_name": display_name,
                            "normalized_key": normalize_key(display_name),
                            "normalized_group": group_name,
                            "content_type": result.content_type,
                            "inferred_country": result.country,
                            "inferred_language": result.language,
                            "inferred_category": result.category,
                            "claimed_quality": result.quality,
                            "normalized_at": utcnow(),
                            "normalization_explanations_json": list(result.explanations),
                            "visibility_status": filtering.visibility_status,
                            "filtering_explanations_json": list(filtering.explanations),
                        }
                    )
                    decision_rows.append(
                        {
                            "id": str(uuid.uuid4()),
                            "created_at": utcnow(),
                            "updated_at": utcnow(),
                            "raw_channel_id": channel.id,
                            "filter_rule_id": None,
                            "action": filtering.action,
                            "reasons_json": list(filtering.reasons),
                            "is_automatic": channel.manual_visibility_status is None,
                        }
                    )
                    stats.update({result.group_name: 1, result.content_type: 1})
                    last_id = channel.id
                self.db.bulk_update_mappings(RawChannel, raw_updates)
                self.db.bulk_insert_mappings(FilterDecision, decision_rows)
                processed += len(channels)
                job.processed_raw_channels = processed
                job.progress_percent = self._progress(processed, total, lower=5, upper=70)
                job.message = f"Normalized {processed:,} of {total:,} raw channels."
                self.db.commit()

            duplicate_stats = self._build_duplicate_clusters(source_id=job.source_id)
            curated_stats = self._rebuild_curated_lineup(source_id=job.source_id)
            completed_at = utcnow()
            job.status = "succeeded"
            job.completed_at = completed_at
            job.progress_percent = 100
            job.message = "Channel normalization completed."
            job.stats_json = {
                "normalized_channels": processed,
                "groups": dict(stats),
                "duplicate_clusters": duplicate_stats,
                "curated_lineup": curated_stats,
            }
        except Exception as exc:
            self.db.rollback()
            job = self.db.get(NormalizationJob, job_id)
            if job is None:
                raise
            message = redact_text(str(exc) or "Channel normalization failed.")
            job.status = "failed"
            job.progress_percent = 100
            job.message = message
            job.failure_reason = message
            job.completed_at = utcnow()
        self.db.commit()
        job = self.db.get(NormalizationJob, job_id)
        if job is None:
            raise NormalizationJobNotFoundError()
        return self._job_response(job)

    def cleanup_queues(self, *, source_id: str | None = None) -> CleanupQueuesResponse:
        filters = self._raw_channel_filters(source_id=source_id)
        duplicate_count = self.db.scalar(
            select(func.count()).select_from(RawChannel).where(*filters, RawChannel.duplicate_cluster_id.is_not(None))
        ) or 0
        missing_count = self.db.scalar(
            select(func.count())
            .select_from(RawChannel)
            .where(*filters, or_(RawChannel.normalized_key.is_(None), RawChannel.normalized_key.in_(("", "unnamed-channel"))))
        ) or 0
        hidden_count = self.db.scalar(
            select(func.count()).select_from(RawChannel).where(*filters, RawChannel.visibility_status == "hidden")
        ) or 0
        unclassified_count = self.db.scalar(
            select(func.count()).select_from(RawChannel).where(*filters, RawChannel.normalized_group == "Other")
        ) or 0
        newly_imported_count = self.db.scalar(
            select(func.count()).select_from(RawChannel).where(*filters, RawChannel.normalized_at.is_(None))
        ) or 0
        reason_counts = self._reason_counts(source_id=source_id)
        queues = [
            ("duplicates", "Duplicate candidates", duplicate_count, "Conservative clusters awaiting review."),
            ("missing_names", "Missing or malformed names", missing_count, "Channels with weak display metadata."),
            ("test_backup", "Test and backup streams", reason_counts["test or backup stream"], "Likely backup/test feeds."),
            ("low_quality_duplicates", "Low-quality duplicates", reason_counts["low-quality duplicate"], "Lower-quality entries where a better candidate exists."),
            ("unclassified", "Unclassified channels", unclassified_count, "Channels mapped to Other."),
            ("suspected_adult", "Suspected adult", reason_counts["suspected adult content"], "Adult content detected by name/group patterns."),
            ("shopping_religious", "Shopping and religious", reason_counts["shopping channel"] + reason_counts["religious channel"], "Optional category cleanup."),
            ("foreign_language", "Foreign language", reason_counts["foreign-language channel"], "Channels inferred as non-English."),
            ("newly_imported", "Newly imported", newly_imported_count, "Raw channels not normalized yet."),
            ("automatically_hidden", "Automatically hidden", hidden_count, "Channels hidden by cleanup profiles."),
        ]
        return CleanupQueuesResponse(
            queues=[
                CleanupQueueResponse(key=key, label=label, count=count, description=description)
                for key, label, count, description in queues
            ]
        )

    def preview_cleanup_profile(
        self,
        *,
        profile: FilterProfile,
        source_id: str | None,
    ) -> CleanupPreviewResponse:
        preview = self._preview_profile(profile=profile, source_id=source_id)
        return CleanupPreviewResponse(
            profile=profile,
            source_id=source_id,
            total_channels=preview.total_channels,
            would_hide=preview.would_hide,
            would_allow=preview.would_allow,
            protected_count=preview.protected_count,
            sample_channel_ids=preview.sample_channel_ids,
            reasons=preview.reasons,
        )

    def apply_cleanup_profile(
        self,
        *,
        profile: FilterProfile,
        source_id: str | None,
    ) -> CleanupApplyResponse:
        response = self.create_normalization_job(source_id=source_id, profile=profile, process_now=True)
        preview = self._preview_profile(profile=profile, source_id=source_id)
        return CleanupApplyResponse(
            profile=profile,
            source_id=source_id,
            total_channels=preview.total_channels,
            would_hide=preview.would_hide,
            would_allow=preview.would_allow,
            protected_count=preview.protected_count,
            sample_channel_ids=preview.sample_channel_ids,
            reasons={**preview.reasons, "normalization_job_succeeded": int(response.status == "succeeded")},
            applied=response.status == "succeeded",
        )

    def protection_summary(self, *, source_id: str | None = None) -> ProtectionSummaryResponse:
        filters = self._raw_channel_filters(source_id=source_id)
        protected_channel_count = self.db.scalar(
            select(func.count()).select_from(RawChannel).where(*filters, RawChannel.protected_from_auto_merge.is_(True))
        ) or 0
        protected_cluster_count = self._protected_cluster_count(source_id=source_id)
        return ProtectionSummaryResponse(
            protected_channel_count=protected_channel_count,
            protected_cluster_count=protected_cluster_count,
            total_protection_count=protected_channel_count + protected_cluster_count,
        )

    def clear_manual_protections(self, *, source_id: str | None = None) -> ClearProtectionsResponse:
        before = self.protection_summary(source_id=source_id)
        filters = self._raw_channel_filters(source_id=source_id)
        self.db.execute(
            update(RawChannel)
            .where(*filters, RawChannel.protected_from_auto_merge.is_(True))
            .values(protected_from_auto_merge=False, updated_at=utcnow())
        )
        for cluster in self._protected_clusters(source_id=source_id):
            cluster.review_status = "pending_review"
            cluster.updated_at = utcnow()
        self.db.commit()
        return ClearProtectionsResponse(
            protected_channel_count=0,
            protected_cluster_count=0,
            total_protection_count=0,
            message=f"Cleared {before.total_protection_count:,} manual protection override(s).",
        )

    def list_duplicate_clusters(self) -> DuplicateClusterListResponse:
        clusters = self.db.scalars(
            select(DuplicateCluster)
            .order_by(DuplicateCluster.confidence_score.desc(), DuplicateCluster.created_at.asc())
            .limit(200)
        ).all()
        return DuplicateClusterListResponse(clusters=[self._cluster_response(cluster) for cluster in clusters])

    def protect_duplicate_cluster(self, cluster_id: str) -> DuplicateActionResponse:
        cluster = self._get_cluster(cluster_id)
        now = utcnow()
        cluster.review_status = "protected"
        cluster.updated_at = now
        for channel in self._cluster_channels(cluster):
            channel.protected_from_auto_merge = True
            channel.updated_at = now
        self.db.commit()
        return DuplicateActionResponse(
            cluster=self._cluster_response(cluster),
            message="Cluster protected; raw channels will not be auto-merged.",
        )

    def unprotect_duplicate_cluster(self, cluster_id: str) -> DuplicateActionResponse:
        cluster = self._get_cluster(cluster_id)
        now = utcnow()
        channels = self._cluster_channels(cluster)
        if cluster.review_status == "protected":
            cluster.review_status = "pending_review"
        cluster.updated_at = now
        for channel in channels:
            channel.protected_from_auto_merge = False
            channel.updated_at = now
        self.db.commit()
        return DuplicateActionResponse(
            cluster=self._cluster_response(cluster),
            message="Cluster protection cleared; raw channels and visibility decisions were preserved.",
        )

    def merge_duplicate_cluster(self, cluster_id: str) -> DuplicateActionResponse:
        cluster = self._get_cluster(cluster_id)
        cluster.review_status = "merged"
        self.db.commit()
        return DuplicateActionResponse(
            cluster=self._cluster_response(cluster),
            message="Cluster marked as merged in the curated lineup.",
        )

    def split_duplicate_cluster(self, cluster_id: str) -> DuplicateActionResponse:
        cluster = self._get_cluster(cluster_id)
        self.db.execute(
            update(RawChannel)
            .where(RawChannel.duplicate_cluster_id == cluster.id)
            .values(duplicate_cluster_id=None, protected_from_auto_merge=True, updated_at=utcnow())
        )
        cluster.review_status = "split"
        self.db.commit()
        return DuplicateActionResponse(
            cluster=self._cluster_response(cluster),
            message="Cluster split and protected from automatic re-clustering.",
        )

    def _normalize_raw_channel(self, channel: RawChannel) -> NormalizationResult:
        source_content_type = channel.source_metadata_json.get("content_type")
        return normalize_channel(
            original_name=channel.original_name,
            original_group=channel.original_group,
            source_content_type=source_content_type if isinstance(source_content_type, str) else None,
            stream_url=channel.original_url,
            attributes={str(key): str(value) for key, value in channel.raw_attributes_json.items()},
        )

    def _build_duplicate_clusters(self, *, source_id: str | None) -> dict[str, int]:
        filters = self._raw_channel_filters(source_id=source_id)
        cluster_count = 0
        candidate_count = 0
        duplicate_buckets = self.db.execute(
            select(RawChannel.normalized_key, func.count())
            .where(
                *filters,
                RawChannel.normalized_key.is_not(None),
                RawChannel.visibility_status.in_(("visible", "always_visible")),
                RawChannel.protected_from_auto_merge.is_(False),
            )
            .group_by(RawChannel.normalized_key)
            .having(func.count() > 1)
        ).all()
        for normalized_key, _count in duplicate_buckets:
            channels = self.db.scalars(
                select(RawChannel)
                .where(
                    *filters,
                    RawChannel.normalized_key == normalized_key,
                    RawChannel.visibility_status.in_(("visible", "always_visible")),
                    RawChannel.protected_from_auto_merge.is_(False),
                )
                .order_by(RawChannel.claimed_quality.desc(), RawChannel.original_name.asc())
            ).all()
            if len(channels) < 2 or not self._channels_can_cluster(channels):
                continue
            evaluations = [
                duplicate_confidence(
                    left_key=channels[0].normalized_key,
                    right_key=channel.normalized_key,
                    left_tvg_id=channels[0].original_tvg_id,
                    right_tvg_id=channel.original_tvg_id,
                    left_country=channels[0].inferred_country,
                    right_country=channel.inferred_country,
                    left_language=channels[0].inferred_language,
                    right_language=channel.inferred_language,
                    left_quality=channels[0].claimed_quality,
                    right_quality=channel.claimed_quality,
                    left_url_checksum=channels[0].url_checksum,
                    right_url_checksum=channel.url_checksum,
                )
                for channel in channels[1:]
            ]
            if not evaluations or not all(evaluation.safe_to_cluster for evaluation in evaluations):
                continue
            confidence = min(evaluation.confidence for evaluation in evaluations)
            primary = self._primary_channel(channels)
            cluster = DuplicateCluster(
                label=primary.normalized_name or primary.original_name,
                confidence_score=confidence,
                review_status="auto_merged" if confidence >= 0.95 else "pending_review",
                candidate_count=len(channels),
                primary_raw_channel_id=primary.id,
                explanation_json=[
                    {"reason": reason}
                    for evaluation in evaluations
                    for reason in evaluation.reasons
                ],
                stats_json={"normalized_key": normalized_key},
            )
            self.db.add(cluster)
            self.db.flush()
            for channel in channels:
                channel.duplicate_cluster_id = cluster.id
            cluster_count += 1
            candidate_count += len(channels)
        self.db.commit()
        return {"clusters": cluster_count, "candidates": candidate_count}

    def _rebuild_curated_lineup(self, *, source_id: str | None) -> dict[str, int]:
        filters = self._raw_channel_filters(source_id=source_id)
        channels = self.db.scalars(
            select(RawChannel)
            .where(*filters, RawChannel.visibility_status.in_(("visible", "always_visible")))
            .order_by(RawChannel.normalized_group.asc(), RawChannel.normalized_name.asc(), RawChannel.id.asc())
        ).all()
        group_ids = {group.normalized_name: group.id for group in self.db.scalars(select(ChannelGroup)).all()}
        grouped_channels: dict[str, list[RawChannel]] = defaultdict(list)
        for channel in channels:
            group_key = channel.duplicate_cluster_id or channel.id
            grouped_channels[group_key].append(channel)

        curated_rows: list[dict[str, object]] = []
        candidate_rows: list[dict[str, object]] = []
        sort_order = 0
        for channel_group in grouped_channels.values():
            primary = self._primary_channel(channel_group)
            curated_id = str(uuid.uuid4())
            group_id = group_ids.get(normalize_key(primary.normalized_group or "Other"))
            curated_rows.append(
                {
                    "id": curated_id,
                    "created_at": utcnow(),
                    "updated_at": utcnow(),
                    "group_id": group_id,
                    "duplicate_cluster_id": primary.duplicate_cluster_id,
                    "name": primary.normalized_name or primary.original_name,
                    "normalized_name": primary.normalized_key or normalize_key(primary.original_name),
                    "content_type": primary.content_type,
                    "logo_url": primary.original_logo_url,
                    "visibility_status": "visible",
                    "source_candidate_count": len(channel_group),
                    "sort_order": sort_order,
                }
            )
            ranked_channels = sorted(channel_group, key=self._candidate_sort_key)
            for rank, candidate in enumerate(ranked_channels):
                candidate_rows.append(
                    {
                        "id": str(uuid.uuid4()),
                        "created_at": utcnow(),
                        "updated_at": utcnow(),
                        "curated_channel_id": curated_id,
                        "raw_channel_id": candidate.id,
                        "role": "primary" if candidate.id == primary.id else "backup",
                        "rank": rank,
                        "selection_reason": "Selected by quality and duplicate confidence."
                        if candidate.id == primary.id
                        else "Retained as a backup source candidate.",
                    }
                )
            sort_order += 1
            if len(curated_rows) >= self.settings.channel_normalization_batch_size:
                self.db.bulk_insert_mappings(CuratedChannel, curated_rows)
                self.db.bulk_insert_mappings(ChannelSourceCandidate, candidate_rows)
                curated_rows.clear()
                candidate_rows.clear()
        if curated_rows:
            self.db.bulk_insert_mappings(CuratedChannel, curated_rows)
            self.db.bulk_insert_mappings(ChannelSourceCandidate, candidate_rows)
        self.db.commit()
        return {"curated_channels": sort_order, "source_candidates": len(channels)}

    def _channels_can_cluster(self, channels: list[RawChannel]) -> bool:
        countries = {channel.inferred_country for channel in channels if channel.inferred_country}
        languages = {channel.inferred_language for channel in channels if channel.inferred_language}
        tvg_ids = {channel.original_tvg_id for channel in channels if channel.original_tvg_id}
        checksums = {channel.url_checksum for channel in channels if channel.url_checksum}
        has_strong_identifier = len(tvg_ids) == 1 or len(checksums) == 1
        if (len(countries) > 1 or len(languages) > 1) and not has_strong_identifier:
            return False
        return True

    def _reset_generated_lineup(self, *, source_id: str | None) -> None:
        filters = self._raw_channel_filters(source_id=source_id)
        if source_id is None:
            self.db.execute(delete(ChannelSourceCandidate))
            self.db.execute(delete(CuratedChannel))
            self.db.execute(delete(DuplicateCluster))
        else:
            raw_ids = select(RawChannel.id).where(*filters)
            curated_ids = [
                row[0]
                for row in self.db.execute(
                    select(ChannelSourceCandidate.curated_channel_id).where(
                        ChannelSourceCandidate.raw_channel_id.in_(raw_ids)
                    )
                ).all()
            ]
            cluster_ids = [
                row[0]
                for row in self.db.execute(
                    select(RawChannel.duplicate_cluster_id)
                    .where(*filters, RawChannel.duplicate_cluster_id.is_not(None))
                    .distinct()
                ).all()
                if row[0] is not None
            ]
            self.db.execute(
                delete(ChannelSourceCandidate).where(ChannelSourceCandidate.raw_channel_id.in_(raw_ids))
            )
            if curated_ids:
                self.db.execute(delete(CuratedChannel).where(CuratedChannel.id.in_(curated_ids)))
            if cluster_ids:
                self.db.execute(delete(DuplicateCluster).where(DuplicateCluster.id.in_(cluster_ids)))
        self.db.execute(
            update(RawChannel)
            .where(*filters)
            .values(duplicate_cluster_id=None, updated_at=utcnow())
        )
        self.db.commit()

    def _delete_automatic_filter_decisions(self, *, source_id: str | None) -> None:
        filters = self._raw_channel_filters(source_id=source_id)
        raw_ids = select(RawChannel.id).where(*filters)
        self.db.execute(
            delete(FilterDecision).where(
                FilterDecision.is_automatic.is_(True),
                FilterDecision.raw_channel_id.in_(raw_ids),
            )
        )
        self.db.commit()

    def _preview_profile(self, *, profile: FilterProfile, source_id: str | None) -> CleanupPreview:
        filters = self._raw_channel_filters(source_id=source_id)
        total_channels = 0
        would_hide = 0
        would_allow = 0
        protected_count = 0
        sample_channel_ids: list[str] = []
        reasons: Counter[str] = Counter()
        last_id: str | None = None
        while True:
            batch_filters = list(filters)
            if last_id is not None:
                batch_filters.append(RawChannel.id > last_id)
            channels = self.db.scalars(
                select(RawChannel)
                .where(*batch_filters)
                .order_by(RawChannel.id.asc())
                .limit(self.settings.channel_normalization_batch_size)
            ).all()
            if not channels:
                break
            for channel in channels:
                result = self._normalize_raw_channel(channel)
                filtering = evaluate_filter(
                    result,
                    profile=profile,
                    manual_visibility_status=channel.manual_visibility_status,
                )
                total_channels += 1
                if channel.protected_from_auto_merge:
                    protected_count += 1
                if filtering.visibility_status == "hidden":
                    would_hide += 1
                    if len(sample_channel_ids) < 25:
                        sample_channel_ids.append(channel.id)
                    reasons.update(filtering.reasons)
                else:
                    would_allow += 1
                last_id = channel.id
        return CleanupPreview(
            total_channels=total_channels,
            would_hide=would_hide,
            would_allow=would_allow,
            protected_count=protected_count,
            sample_channel_ids=sample_channel_ids,
            reasons=dict(reasons),
        )

    def _reason_counts(self, *, source_id: str | None) -> Counter[str]:
        filters = self._raw_channel_filters(source_id=source_id)
        reasons: Counter[str] = Counter()
        last_id: str | None = None
        while True:
            batch_filters = list(filters)
            if last_id is not None:
                batch_filters.append(RawChannel.id > last_id)
            channels = self.db.scalars(
                select(RawChannel)
                .where(*batch_filters)
                .order_by(RawChannel.id.asc())
                .limit(self.settings.channel_normalization_batch_size)
            ).all()
            if not channels:
                break
            for channel in channels:
                result = self._normalize_raw_channel(channel)
                reasons.update(automatic_filter_reasons(result, "aggressive"))
                if channel.duplicate_cluster_id and channel.claimed_quality == "SD":
                    reasons.update({"low-quality duplicate": 1})
                last_id = channel.id
        return reasons

    def _ensure_standard_groups(self) -> None:
        existing = {
            group.normalized_name
            for group in self.db.scalars(select(ChannelGroup)).all()
        }
        for sort_order, group_name in enumerate(STANDARD_GROUPS):
            group_key = normalize_key(group_name)
            if group_key not in existing:
                self.db.add(
                    ChannelGroup(
                        name=group_name,
                        normalized_name=group_key,
                        sort_order=sort_order,
                        is_visible=True,
                    )
                )
        self.db.flush()

    def _canonical_group_name(self, group_name: str) -> str:
        requested_key = normalize_key(group_name)
        for standard_group in STANDARD_GROUPS:
            if normalize_key(standard_group) == requested_key:
                return standard_group
        return "Other"

    def _raw_channel_filters(self, *, source_id: str | None) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = []
        if source_id is not None:
            filters.append(RawChannel.source_id == source_id)
        return filters

    def _source_names(self, source_ids: set[str]) -> dict[str, str]:
        if not source_ids:
            return {}
        sources = self.db.scalars(select(Source).where(Source.id.in_(source_ids))).all()
        return {source.id: source.name for source in sources}

    def _channel_response(self, channel: RawChannel, source_name: str | None) -> ChannelSummaryResponse:
        return ChannelSummaryResponse(
            id=channel.id,
            source_id=channel.source_id,
            source_name=source_name,
            original_name=channel.original_name,
            normalized_name=channel.normalized_name,
            normalized_group=channel.normalized_group,
            content_type=cast(ContentType, channel.content_type),
            inferred_country=channel.inferred_country,
            inferred_language=channel.inferred_language,
            inferred_category=channel.inferred_category,
            claimed_quality=channel.claimed_quality,
            visibility_status=channel.visibility_status,
            protected_from_auto_merge=channel.protected_from_auto_merge,
            duplicate_cluster_id=channel.duplicate_cluster_id,
            url_checksum=channel.url_checksum,
            original_tvg_id=channel.original_tvg_id,
            original_tvg_name=channel.original_tvg_name,
            original_logo_url=redact_text(channel.original_logo_url) if channel.original_logo_url else None,
            line_number=channel.line_number,
            normalized_at=channel.normalized_at,
            explanations=[
                {str(key): str(value) for key, value in item.items()}
                for item in channel.normalization_explanations_json
                if isinstance(item, dict)
            ],
            filtering_reasons=[
                cast(dict[str, object], redact_payload(item))
                for item in channel.filtering_explanations_json
                if isinstance(item, dict)
            ],
        )

    def _candidate_response(
        self,
        candidate: ChannelSourceCandidate,
        raw_channel: RawChannel,
    ) -> ChannelSourceCandidateResponse:
        return ChannelSourceCandidateResponse(
            id=candidate.id,
            raw_channel_id=raw_channel.id,
            curated_channel_id=candidate.curated_channel_id,
            role=candidate.role,
            rank=candidate.rank,
            selection_reason=candidate.selection_reason,
            original_name=raw_channel.original_name,
            normalized_name=raw_channel.normalized_name,
            normalized_group=raw_channel.normalized_group,
            content_type=cast(ContentType, raw_channel.content_type),
            claimed_quality=raw_channel.claimed_quality,
            url_checksum=raw_channel.url_checksum,
            attributes=cast(dict[str, object], redact_payload(raw_channel.raw_attributes_json)),
        )

    def _job_response(self, job: NormalizationJob) -> NormalizationJobResponse:
        return NormalizationJobResponse(
            id=job.id,
            source_id=job.source_id,
            status=cast(JobStatus, job.status),
            profile=cast(FilterProfile, job.profile),
            progress_percent=job.progress_percent,
            message=redact_text(job.message),
            total_raw_channels=job.total_raw_channels,
            processed_raw_channels=job.processed_raw_channels,
            started_at=job.started_at,
            completed_at=job.completed_at,
            canceled_at=job.canceled_at,
            failure_reason=redact_text(job.failure_reason) if job.failure_reason else None,
            stats=cast(dict[str, object], redact_payload(job.stats_json)),
        )

    def _cluster_response(self, cluster: DuplicateCluster) -> DuplicateClusterResponse:
        return DuplicateClusterResponse(
            id=cluster.id,
            label=cluster.label,
            confidence_score=cluster.confidence_score,
            review_status=cluster.review_status,
            candidate_count=cluster.candidate_count,
            primary_raw_channel_id=cluster.primary_raw_channel_id,
            explanations=[
                cast(dict[str, object], redact_payload(item))
                for item in cluster.explanation_json
                if isinstance(item, dict)
            ],
        )

    def _get_cluster(self, cluster_id: str) -> DuplicateCluster:
        cluster = self.db.get(DuplicateCluster, cluster_id)
        if cluster is None:
            raise DuplicateClusterNotFoundError()
        return cluster

    def _cluster_channels(self, cluster: DuplicateCluster) -> list[RawChannel]:
        channels = self.db.scalars(select(RawChannel).where(RawChannel.duplicate_cluster_id == cluster.id)).all()
        if channels or cluster.review_status != "protected":
            return list(channels)

        normalized_key = cluster.stats_json.get("normalized_key")
        if not isinstance(normalized_key, str) or not normalized_key:
            return []

        fallback_filters: list[ColumnElement[bool]] = [
            RawChannel.normalized_key == normalized_key,
            RawChannel.protected_from_auto_merge.is_(True),
        ]
        if cluster.primary_raw_channel_id:
            primary = self.db.get(RawChannel, cluster.primary_raw_channel_id)
            if primary is not None:
                fallback_filters.append(RawChannel.source_id == primary.source_id)
        return list(self.db.scalars(select(RawChannel).where(*fallback_filters)).all())

    def _protected_clusters(self, *, source_id: str | None) -> list[DuplicateCluster]:
        if source_id is None:
            return list(
                self.db.scalars(
                    select(DuplicateCluster).where(DuplicateCluster.review_status == "protected")
                ).all()
            )
        return list(
            self.db.scalars(
                select(DuplicateCluster)
                .join(RawChannel, RawChannel.duplicate_cluster_id == DuplicateCluster.id)
                .where(RawChannel.source_id == source_id, DuplicateCluster.review_status == "protected")
                .distinct()
            ).all()
        )

    def _protected_cluster_count(self, *, source_id: str | None) -> int:
        if source_id is None:
            return self.db.scalar(
                select(func.count()).select_from(DuplicateCluster).where(DuplicateCluster.review_status == "protected")
            ) or 0
        return self.db.scalar(
            select(func.count(func.distinct(DuplicateCluster.id)))
            .select_from(DuplicateCluster)
            .join(RawChannel, RawChannel.duplicate_cluster_id == DuplicateCluster.id)
            .where(RawChannel.source_id == source_id, DuplicateCluster.review_status == "protected")
        ) or 0

    @staticmethod
    def _primary_channel(channels: list[RawChannel]) -> RawChannel:
        return sorted(channels, key=ChannelService._candidate_sort_key)[0]

    @staticmethod
    def _candidate_sort_key(channel: RawChannel) -> tuple[int, str]:
        quality_rank = QUALITY_RANK.get(channel.claimed_quality or "", 0)
        return (-quality_rank, channel.normalized_name or channel.original_name)

    @staticmethod
    def _encode_cursor(offset: int) -> str:
        payload = json.dumps({"offset": offset}).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("ascii")

    @staticmethod
    def _decode_cursor(cursor: str | None) -> int:
        if cursor is None:
            return 0
        try:
            payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8"))
        except (ValueError, json.JSONDecodeError) as exc:
            raise SourceValidationError("Invalid channel cursor.") from exc
        offset = payload.get("offset")
        if not isinstance(offset, int) or offset < 0:
            raise SourceValidationError("Invalid channel cursor.")
        return offset

    @staticmethod
    def _progress(processed: int, total: int, *, lower: int, upper: int) -> int:
        if total <= 0:
            return upper
        return min(upper, lower + int(((upper - lower) * processed) / total))
