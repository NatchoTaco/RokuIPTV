from __future__ import annotations

import hashlib
import math
import socket
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import httpx
from fastapi import UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from streamforge_api.core.config import Settings
from streamforge_api.core.errors import (
    ImportJobNotFoundError,
    SourceDisabledError,
    SourceNotFoundError,
    SourceValidationError,
)
from streamforge_api.core.redaction import redact_text
from streamforge_api.core.secrets import SecretBox
from streamforge_api.domain.m3u import (
    CONTENT_TYPE_LABELS,
    ContentType,
    M3uChannel,
    M3uParseResult,
    M3uParser,
)
from streamforge_api.domain.source_status import (
    ImportJobState,
    PlaylistImportState,
    SourceState,
    SourceType,
)
from streamforge_api.domain.url_safety import SafeUrlValidator
from streamforge_api.models import (
    PlaylistImport,
    PlaylistImportJob,
    RawChannel,
    Source,
    SourceStatus,
    User,
    utcnow,
)
from streamforge_api.schemas.sources import (
    PlaylistImportHistoryItem,
    PlaylistImportHistoryResponse,
    PlaylistImportJobResponse,
    SourceCreatedResponse,
    SourceListResponse,
    SourceSummaryResponse,
    SourceValidationResponse,
)


@dataclass(frozen=True)
class LoadedPlaylist:
    path: Path
    source_version: str
    temporary: bool = False


class SourceImportService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.secret_box = SecretBox(settings)
        self.url_validator = SafeUrlValidator(
            allow_private_destinations=settings.allow_private_source_urls
        )
        self.parser = M3uParser(self.url_validator)

    def list_sources(self) -> SourceListResponse:
        sources = self.db.scalars(
            select(Source).where(Source.deleted_at.is_(None)).order_by(Source.updated_at.desc())
        ).all()
        return SourceListResponse(sources=[self._source_summary(source) for source in sources])

    def list_import_history(self, *, source_id: str | None = None) -> PlaylistImportHistoryResponse:
        statement = (
            select(PlaylistImport, Source)
            .join(Source, Source.id == PlaylistImport.source_id)
            .order_by(PlaylistImport.created_at.desc())
        )
        if source_id is not None:
            statement = statement.where(PlaylistImport.source_id == source_id)
        imports = [
            self._import_history_item(playlist_import, source)
            for playlist_import, source in self.db.execute(statement).all()
        ]
        return PlaylistImportHistoryResponse(imports=imports)

    def get_job(self, job_id: str) -> PlaylistImportJobResponse:
        job = self.db.get(PlaylistImportJob, job_id)
        if job is None:
            raise ImportJobNotFoundError()
        return self._job_response(job)

    def validate_url_source(
        self,
        raw_url: str,
        *,
        enabled_content_types: list[ContentType] | None = None,
    ) -> SourceValidationResponse:
        url_result = self.url_validator.validate_source_url(raw_url)
        if not url_result.is_safe or url_result.normalized_url is None:
            return SourceValidationResponse(
                playlist_reachable=False,
                channel_count=0,
                group_count=0,
                estimated_import_time_seconds=0,
                warnings=[],
                errors=url_result.errors,
            )
        warnings = self._source_url_warnings(url_result.normalized_url)
        requested_content_types = self._requested_content_types(enabled_content_types)
        selected_content_types = self._enabled_content_types(enabled_content_types)
        try:
            playlist = self._fetch_remote_playlist(url_result.normalized_url)
        except SourceValidationError as exc:
            return SourceValidationResponse(
                playlist_reachable=False,
                channel_count=0,
                group_count=0,
                estimated_import_time_seconds=0,
                warnings=warnings,
                errors=[exc.public_message],
            )
        try:
            parse_result = self.parser.parse_path(
                playlist.path,
                include_content_types=selected_content_types,
            )
            return self._validation_response(
                parse_result,
                reachable=True,
                extra_warnings=warnings,
                selected_content_types=selected_content_types,
                requested_content_types=requested_content_types,
            )
        finally:
            self._cleanup_loaded_playlist(playlist)

    def validate_uploaded_playlist(
        self,
        content: bytes,
        *,
        enabled_content_types: list[ContentType] | None = None,
    ) -> SourceValidationResponse:
        if len(content) > self.settings.source_max_playlist_bytes:
            return SourceValidationResponse(
                playlist_reachable=False,
                channel_count=0,
                group_count=0,
                estimated_import_time_seconds=0,
                warnings=[],
                errors=["Uploaded playlist exceeds the configured maximum size."],
            )
        return self._validation_response(
            self.parser.parse_bytes(
                content,
                include_content_types=self._enabled_content_types(enabled_content_types),
            ),
            reachable=True,
            extra_warnings=[],
            selected_content_types=self._enabled_content_types(enabled_content_types),
            requested_content_types=self._requested_content_types(enabled_content_types),
        )

    def validate_uploaded_playlist_path(
        self,
        path: Path,
        *,
        enabled_content_types: list[ContentType] | None = None,
    ) -> SourceValidationResponse:
        if path.stat().st_size > self.settings.source_max_playlist_bytes:
            return SourceValidationResponse(
                playlist_reachable=False,
                channel_count=0,
                group_count=0,
                estimated_import_time_seconds=0,
                warnings=[],
                errors=["Uploaded playlist exceeds the configured maximum size."],
            )
        return self._validation_response(
            self.parser.parse_path(
                path,
                include_content_types=self._enabled_content_types(enabled_content_types),
            ),
            reachable=True,
            extra_warnings=[],
            selected_content_types=self._enabled_content_types(enabled_content_types),
            requested_content_types=self._requested_content_types(enabled_content_types),
        )

    def create_url_source(
        self,
        *,
        name: str,
        raw_url: str,
        refresh_interval_minutes: int | None,
        enabled_content_types: list[ContentType] | None,
        confirm_large_import: bool,
        actor: User,
    ) -> SourceCreatedResponse:
        url_result = self.url_validator.validate_source_url(raw_url, resolve_dns=False)
        if not url_result.is_safe or url_result.normalized_url is None:
            raise SourceValidationError(" ".join(url_result.errors))
        selected_content_types = self._enabled_content_types(enabled_content_types)
        self._ensure_supported_content_type_selection(selected_content_types)
        next_refresh_at = self._next_refresh_time(refresh_interval_minutes)
        source = Source(
            name=name.strip(),
            source_type="m3u_url",
            status="importing",
            config_json={
                "display_location": url_result.display_url,
                "refresh_interval_minutes": refresh_interval_minutes,
                "enabled_content_types": sorted(selected_content_types),
                "large_import_confirmed": confirm_large_import,
            },
            secret_config_encrypted=self.secret_box.encrypt_json({"url": url_result.normalized_url}),
            refresh_interval_minutes=refresh_interval_minutes,
            next_refresh_at=next_refresh_at,
            is_enabled=True,
        )
        self.db.add(source)
        self.db.flush()
        self._ensure_source_status(source, "importing", "Queued for initial playlist import.")
        job = self._queue_import_job(source, actor=actor, message="Queued initial playlist import.")
        self.db.commit()
        return SourceCreatedResponse(source=self._source_summary(source), job=self._job_response(job))

    def create_upload_source(
        self,
        *,
        name: str,
        filename: str,
        content: bytes,
        refresh_interval_minutes: int | None,
        enabled_content_types: list[ContentType] | None,
        confirm_large_import: bool,
        actor: User,
    ) -> SourceCreatedResponse:
        validation = self.validate_uploaded_playlist(
            content,
            enabled_content_types=enabled_content_types,
        )
        if not validation.playlist_reachable:
            raise SourceValidationError(" ".join(validation.errors))
        selected_content_types = self._enabled_content_types(enabled_content_types)
        self._ensure_supported_content_type_selection(selected_content_types)
        stored_path = self._store_upload(filename, content)
        source = Source(
            name=name.strip(),
            source_type="m3u_upload",
            status="importing",
            config_json={
                "display_location": self._safe_filename(filename),
                "upload_filename": self._safe_filename(filename),
                "refresh_interval_minutes": refresh_interval_minutes,
                "enabled_content_types": sorted(selected_content_types),
                "large_import_confirmed": confirm_large_import,
            },
            secret_config_encrypted=self.secret_box.encrypt_json({"stored_path": str(stored_path)}),
            refresh_interval_minutes=refresh_interval_minutes,
            next_refresh_at=self._next_refresh_time(refresh_interval_minutes),
            is_enabled=True,
        )
        self.db.add(source)
        self.db.flush()
        self._ensure_source_status(source, "importing", "Queued uploaded playlist import.")
        job = self._queue_import_job(source, actor=actor, message="Queued uploaded playlist import.")
        self.db.commit()
        return SourceCreatedResponse(source=self._source_summary(source), job=self._job_response(job))

    def create_upload_source_from_path(
        self,
        *,
        name: str,
        filename: str,
        stored_path: Path,
        refresh_interval_minutes: int | None,
        enabled_content_types: list[ContentType] | None,
        confirm_large_import: bool,
        actor: User,
    ) -> SourceCreatedResponse:
        validation = self.validate_uploaded_playlist_path(
            stored_path,
            enabled_content_types=enabled_content_types,
        )
        if not validation.playlist_reachable:
            stored_path.unlink(missing_ok=True)
            raise SourceValidationError(" ".join(validation.errors))
        selected_content_types = self._enabled_content_types(enabled_content_types)
        self._ensure_supported_content_type_selection(selected_content_types)
        source = Source(
            name=name.strip(),
            source_type="m3u_upload",
            status="importing",
            config_json={
                "display_location": self._safe_filename(filename),
                "upload_filename": self._safe_filename(filename),
                "refresh_interval_minutes": refresh_interval_minutes,
                "enabled_content_types": sorted(selected_content_types),
                "large_import_confirmed": confirm_large_import,
            },
            secret_config_encrypted=self.secret_box.encrypt_json({"stored_path": str(stored_path)}),
            refresh_interval_minutes=refresh_interval_minutes,
            next_refresh_at=self._next_refresh_time(refresh_interval_minutes),
            is_enabled=True,
        )
        self.db.add(source)
        self.db.flush()
        self._ensure_source_status(source, "importing", "Queued uploaded playlist import.")
        job = self._queue_import_job(source, actor=actor, message="Queued uploaded playlist import.")
        self.db.commit()
        return SourceCreatedResponse(source=self._source_summary(source), job=self._job_response(job))

    def create_demo_source(
        self,
        *,
        name: str,
        refresh_interval_minutes: int | None,
        enabled_content_types: list[ContentType] | None,
        confirm_large_import: bool,
        actor: User,
    ) -> SourceCreatedResponse:
        selected_content_types = self._enabled_content_types(enabled_content_types)
        self._ensure_supported_content_type_selection(selected_content_types)
        source = Source(
            name=name.strip(),
            source_type="demo_playlist",
            status="importing",
            config_json={
                "display_location": "Built-in synthetic playlist",
                "refresh_interval_minutes": refresh_interval_minutes,
                "enabled_content_types": sorted(selected_content_types),
                "large_import_confirmed": confirm_large_import,
            },
            refresh_interval_minutes=refresh_interval_minutes,
            next_refresh_at=self._next_refresh_time(refresh_interval_minutes),
            is_enabled=True,
        )
        self.db.add(source)
        self.db.flush()
        self._ensure_source_status(source, "importing", "Queued synthetic playlist import.")
        job = self._queue_import_job(source, actor=actor, message="Queued synthetic playlist import.")
        self.db.commit()
        return SourceCreatedResponse(source=self._source_summary(source), job=self._job_response(job))

    def queue_manual_refresh(self, source_id: str, *, actor: User) -> PlaylistImportJobResponse:
        source = self._get_active_source(source_id)
        if not source.is_enabled:
            raise SourceDisabledError()
        job = self._queue_import_job(source, actor=actor, message="Queued manual playlist refresh.")
        self._ensure_source_status(source, "importing", "Queued manual playlist refresh.", job=job)
        self.db.commit()
        return self._job_response(job)

    def update_source(
        self,
        source_id: str,
        *,
        is_enabled: bool | None,
        refresh_interval_minutes: int | None,
    ) -> SourceSummaryResponse:
        source = self._get_active_source(source_id)
        if is_enabled is not None:
            source.is_enabled = is_enabled
            if not is_enabled:
                source.status = "disabled"
                source.next_refresh_at = None
                self._ensure_source_status(source, "disabled", "Source is disabled.")
            elif source.status == "disabled":
                source.status = "pending"
                self._ensure_source_status(source, "pending", "Source is enabled and ready to import.")
        if refresh_interval_minutes is not None:
            source.refresh_interval_minutes = refresh_interval_minutes
            source.next_refresh_at = self._next_refresh_time(refresh_interval_minutes)
            source.config_json = {
                **source.config_json,
                "refresh_interval_minutes": refresh_interval_minutes,
            }
        self.db.commit()
        return self._source_summary(source)

    def delete_source(self, source_id: str) -> None:
        source = self._get_active_source(source_id)
        source.deleted_at = utcnow()
        source.is_enabled = False
        source.status = "disabled"
        source.next_refresh_at = None
        self._ensure_source_status(source, "disabled", "Source was deleted by an administrator.")
        self.db.commit()

    def queue_due_refreshes(self, *, actor: User | None = None) -> int:
        now = utcnow()
        sources = self.db.scalars(
            select(Source).where(
                Source.deleted_at.is_(None),
                Source.is_enabled.is_(True),
                Source.refresh_interval_minutes.is_not(None),
                Source.next_refresh_at.is_not(None),
                Source.next_refresh_at <= now,
            )
        ).all()
        queued = 0
        for source in sources:
            has_active_job = self.db.scalar(
                select(func.count())
                .select_from(PlaylistImportJob)
                .where(
                    PlaylistImportJob.source_id == source.id,
                    PlaylistImportJob.status.in_(("queued", "running")),
                )
            )
            if has_active_job:
                continue
            self._queue_import_job(source, actor=actor, message="Queued scheduled playlist refresh.")
            source.next_refresh_at = self._next_refresh_time(source.refresh_interval_minutes)
            queued += 1
        self.db.commit()
        return queued

    def process_next_queued_job(self, *, worker_id: str | None = None) -> bool:
        job = self.db.scalar(
            select(PlaylistImportJob)
            .where(PlaylistImportJob.status == "queued")
            .order_by(PlaylistImportJob.created_at.asc())
            .limit(1)
        )
        if job is None:
            return False
        job.worker_id = worker_id or socket.gethostname()
        self.db.commit()
        self.process_import_job(job.id)
        return True

    def process_import_job(self, job_id: str) -> PlaylistImportJobResponse:
        job = self.db.get(PlaylistImportJob, job_id)
        if job is None:
            raise ImportJobNotFoundError()
        source = self.db.get(Source, job.source_id)
        if source is None or source.deleted_at is not None:
            self._fail_job(job, "Source was deleted before import could run.")
            self.db.commit()
            return self._job_response(job)
        if not source.is_enabled:
            self._fail_job(job, "Source is disabled.")
            self.db.commit()
            return self._job_response(job)

        started_at = utcnow()
        job.status = "running"
        job.progress_percent = 5
        job.message = "Starting playlist import."
        job.started_at = started_at
        self._ensure_source_status(source, "importing", "Import worker is loading the playlist.", job=job)
        playlist_import = PlaylistImport(
            source_id=source.id,
            triggered_by_user_id=job.triggered_by_user_id,
            source_kind=source.source_type,
            status="running",
            started_at=started_at,
        )
        self.db.add(playlist_import)
        self.db.flush()
        job.playlist_import_id = playlist_import.id
        playlist_import_id = playlist_import.id
        self.db.commit()

        loaded_playlist: LoadedPlaylist | None = None
        try:
            loaded_playlist = self._load_playlist(source)
            self._update_job(job, 25, "Playlist loaded.")
            selected_content_types = self._source_enabled_content_types(source)
            parse_result = self.parser.parse_path(
                loaded_playlist.path,
                include_content_types=selected_content_types,
                keep_channels=False,
            )
            self._update_job(job, 50, "Playlist parsed.")
            self._ensure_import_still_active(source)
            self._ensure_large_import_allowed(source, parse_result)
            if not parse_result.selected_entry_count:
                raise SourceValidationError("No selected Live TV entries were found for import.")
            self._replace_raw_channels(source, playlist_import, loaded_playlist.path, selected_content_types)
            self._update_job(job, 90, "Raw channels stored.")

            completed_at = utcnow()
            duration_ms = self._duration_ms(started_at, completed_at)
            import_warnings = self._validation_warnings(
                parse_result,
                selected_content_types,
                selected_content_types,
            )
            import_status = "warning" if import_warnings or parse_result.failures else "completed"
            playlist_import.status = import_status
            playlist_import.completed_at = completed_at
            playlist_import.duration_ms = duration_ms
            playlist_import.channel_count = parse_result.selected_entry_count
            playlist_import.group_count = parse_result.group_count
            playlist_import.warning_count = len(import_warnings)
            playlist_import.failure_count = len(parse_result.failures)
            playlist_import.warnings_json = [redact_text(item) for item in import_warnings]
            playlist_import.failures_json = [redact_text(item) for item in parse_result.failures]
            playlist_import.checksum = parse_result.checksum
            playlist_import.source_version = loaded_playlist.source_version

            source.status = "warning" if import_status == "warning" else "healthy"
            source.last_refresh_at = completed_at
            source.last_successful_import_at = completed_at
            source.last_error = None
            source.checksum = parse_result.checksum
            source.source_version = loaded_playlist.source_version
            source.next_refresh_at = self._next_refresh_time(source.refresh_interval_minutes)

            status_message = (
                "Imported with warnings." if import_status == "warning" else "Playlist imported successfully."
            )
            self._ensure_source_status(
                source,
                source.status,
                status_message,
                playlist_import=playlist_import,
                job=job,
                channel_count=parse_result.selected_entry_count,
                group_count=parse_result.group_count,
                checked_at=completed_at,
            )
            job.status = "succeeded"
            job.progress_percent = 100
            job.message = status_message
            job.completed_at = completed_at
        except Exception as exc:
            self.db.rollback()
            job = self.db.get(PlaylistImportJob, job_id)
            source = self.db.get(Source, job.source_id) if job is not None else None
            playlist_import = self.db.get(PlaylistImport, playlist_import_id)
            if job is None or source is None or playlist_import is None:
                raise
            completed_at = utcnow()
            public_message = redact_text(str(exc) or "Playlist import failed.")
            playlist_import.status = "failed"
            playlist_import.completed_at = completed_at
            playlist_import.duration_ms = self._duration_ms(started_at, completed_at)
            playlist_import.failure_reason = public_message
            playlist_import.failures_json = [public_message]
            playlist_import.failure_count = 1
            if source.deleted_at is not None or not source.is_enabled:
                source.status = "disabled"
            else:
                source.status = "offline" if isinstance(exc, SourceValidationError) else "failed"
            source.last_failed_import_at = completed_at
            source.last_error = public_message
            source.next_refresh_at = self._next_refresh_time(source.refresh_interval_minutes)
            self._ensure_source_status(
                source,
                source.status,
                public_message,
                playlist_import=playlist_import,
                job=job,
                checked_at=completed_at,
            )
            self._fail_job(job, public_message)
        finally:
            if loaded_playlist is not None:
                self._cleanup_loaded_playlist(loaded_playlist)
        self.db.commit()
        assert job is not None
        return self._job_response(job)

    def _load_playlist(self, source: Source) -> LoadedPlaylist:
        if source.source_type == "demo_playlist":
            demo_path = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_demo_playlist.m3u"
            checksum = M3uParser.checksum_path(demo_path)
            return LoadedPlaylist(path=demo_path, source_version=f"sha256:{checksum[:12]}")

        secrets = self.secret_box.decrypt_json(source.secret_config_encrypted)
        if source.source_type == "m3u_url":
            raw_url = secrets.get("url")
            if not isinstance(raw_url, str):
                raise SourceValidationError("Source URL is missing.")
            return self._fetch_remote_playlist(raw_url)
        if source.source_type == "m3u_upload":
            stored_path = secrets.get("stored_path")
            if not isinstance(stored_path, str):
                raise SourceValidationError("Uploaded playlist path is missing.")
            path = Path(stored_path)
            upload_root = Path(self.settings.source_upload_dir).resolve()
            resolved_path = path.resolve()
            try:
                resolved_path.relative_to(upload_root)
            except ValueError as exc:
                raise SourceValidationError(
                    "Uploaded playlist path is outside the source upload directory."
                ) from exc
            if not path.is_file():
                raise SourceValidationError("Uploaded playlist file is not available.")
            if resolved_path.stat().st_size > self.settings.source_max_playlist_bytes:
                raise SourceValidationError("Uploaded playlist exceeds the configured maximum size.")
            checksum = M3uParser.checksum_path(resolved_path)
            return LoadedPlaylist(path=resolved_path, source_version=f"sha256:{checksum[:12]}")
        raise SourceValidationError("Unsupported source type.")

    def _fetch_remote_playlist(self, raw_url: str) -> LoadedPlaylist:
        current_url = raw_url
        headers = {"User-Agent": "StreamForge/0.1 playlist-validator"}
        download_path = self._temporary_playlist_path()
        try:
            with httpx.Client(timeout=self.settings.source_request_timeout_seconds, headers=headers) as client:
                for _redirect in range(5):
                    url_result = self.url_validator.validate_source_url(current_url)
                    if not url_result.is_safe or url_result.normalized_url is None:
                        raise SourceValidationError(" ".join(url_result.errors))
                    try:
                        with client.stream(
                            "GET",
                            url_result.normalized_url,
                            follow_redirects=False,
                        ) as response:
                            if response.is_redirect:
                                redirect_url = response.headers.get("location")
                                if not redirect_url:
                                    raise SourceValidationError("Playlist redirected without a destination.")
                                current_url = str(httpx.URL(url_result.normalized_url).join(redirect_url))
                                continue
                            if response.status_code >= 400:
                                raise SourceValidationError(f"Playlist returned HTTP {response.status_code}.")
                            self._write_response_to_path(response, download_path)
                            checksum = M3uParser.checksum_path(download_path)
                            return LoadedPlaylist(
                                path=download_path,
                                source_version=f"sha256:{checksum[:12]}",
                                temporary=True,
                            )
                    except httpx.TimeoutException as exc:
                        raise SourceValidationError("Playlist request timed out.") from exc
                    except httpx.HTTPError as exc:
                        raise SourceValidationError("Playlist could not be reached.") from exc
            raise SourceValidationError("Playlist redirected too many times.")
        except Exception:
            download_path.unlink(missing_ok=True)
            raise

    def _replace_raw_channels(
        self,
        source: Source,
        playlist_import: PlaylistImport,
        playlist_path: Path,
        enabled_content_types: set[ContentType],
    ) -> None:
        self._ensure_import_still_active(source)
        self.db.execute(delete(RawChannel).where(RawChannel.source_id == source.id))
        batch: list[dict[str, object]] = []
        for channel in self.parser.iter_channels_path(
            playlist_path,
            include_content_types=enabled_content_types,
        ):
            batch.append(self._raw_channel_mapping(source, playlist_import, channel))
            if len(batch) >= self.settings.source_import_batch_size:
                self._ensure_import_still_active(source)
                self.db.bulk_insert_mappings(RawChannel, batch)
                batch.clear()
        if batch:
            self._ensure_import_still_active(source)
            self.db.bulk_insert_mappings(RawChannel, batch)

    def _raw_channel_mapping(
        self,
        source: Source,
        playlist_import: PlaylistImport,
        channel: M3uChannel,
    ) -> dict[str, object]:
        now = utcnow()
        return {
            "id": str(uuid.uuid4()),
            "created_at": now,
            "updated_at": now,
            "source_id": source.id,
            "playlist_import_id": playlist_import.id,
            "duplicate_cluster_id": None,
            "original_name": channel.original_name,
            "original_group": channel.original_group,
            "original_url": channel.original_url,
            "original_tvg_id": channel.original_tvg_id,
            "original_tvg_name": channel.original_tvg_name,
            "original_logo_url": channel.original_logo_url,
            "source_metadata_json": {
                "duration": channel.duration,
                "content_type": channel.content_type,
            },
            "line_number": channel.line_number,
            "raw_extinf": channel.raw_extinf,
            "raw_attributes_json": channel.attributes,
            "url_checksum": hashlib.sha256(channel.original_url.encode("utf-8")).hexdigest(),
            "normalized_name": None,
            "normalized_group": None,
            "inferred_country": None,
            "inferred_language": None,
            "inferred_category": None,
            "claimed_quality": None,
            "measured_resolution": None,
            "measured_frame_rate": None,
            "codec_information_json": {},
            "epg_status": "unknown",
            "health_status": "unknown",
            "quality_score": None,
            "reliability_score": None,
            "visibility_status": "visible",
            "filtering_explanations_json": [],
        }

    def _write_response_to_path(self, response: httpx.Response, path: Path) -> None:
        bytes_written = 0
        with path.open("wb") as output:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > self.settings.source_max_playlist_bytes:
                    raise SourceValidationError("Playlist exceeds the configured maximum size.")
                output.write(chunk)

    def _temporary_playlist_path(self) -> Path:
        download_dir = Path(self.settings.source_upload_dir) / ".downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        return download_dir / f"{uuid.uuid4()}.m3u"

    @staticmethod
    def _cleanup_loaded_playlist(playlist: LoadedPlaylist) -> None:
        if playlist.temporary:
            playlist.path.unlink(missing_ok=True)

    def _queue_import_job(self, source: Source, *, actor: User | None, message: str) -> PlaylistImportJob:
        job = PlaylistImportJob(
            source_id=source.id,
            triggered_by_user_id=actor.id if actor is not None else None,
            status="queued",
            progress_percent=0,
            message=message,
        )
        self.db.add(job)
        source.status = "importing"
        self.db.flush()
        return job

    def _ensure_source_status(
        self,
        source: Source,
        status: SourceState | str,
        message: str,
        *,
        playlist_import: PlaylistImport | None = None,
        job: PlaylistImportJob | None = None,
        channel_count: int | None = None,
        group_count: int | None = None,
        checked_at: datetime | None = None,
    ) -> SourceStatus:
        source_status = self.db.scalar(select(SourceStatus).where(SourceStatus.source_id == source.id))
        if source_status is None:
            source_status = SourceStatus(source_id=source.id)
            self.db.add(source_status)
        source_status.status = status
        source_status.message = redact_text(message)
        if checked_at is not None:
            source_status.last_checked_at = checked_at
        if status in {"healthy", "warning"}:
            source_status.last_success_at = checked_at or utcnow()
        if status in {"offline", "failed"}:
            source_status.last_failure_at = checked_at or utcnow()
        if playlist_import is not None:
            source_status.last_import_id = playlist_import.id
        if job is not None:
            source_status.last_job_id = job.id
        if channel_count is not None:
            source_status.channel_count = channel_count
        if group_count is not None:
            source_status.group_count = group_count
        return source_status

    def _source_summary(self, source: Source) -> SourceSummaryResponse:
        source_status = self.db.scalar(select(SourceStatus).where(SourceStatus.source_id == source.id))
        active_job = self.db.scalar(
            select(PlaylistImportJob)
            .where(
                PlaylistImportJob.source_id == source.id,
                PlaylistImportJob.status.in_(("queued", "running")),
            )
            .order_by(PlaylistImportJob.created_at.desc())
            .limit(1)
        )
        return SourceSummaryResponse(
            id=source.id,
            name=source.name,
            source_type=cast(SourceType, source.source_type),
            status=cast(SourceState, source.status),
            status_message=redact_text(source_status.message)
            if source_status
            else "Source has not been imported yet.",
            display_location=redact_text(str(source.config_json.get("display_location", "Hidden"))),
            is_enabled=source.is_enabled,
            enabled_content_types=sorted(self._source_enabled_content_types(source)),
            refresh_interval_minutes=source.refresh_interval_minutes,
            last_updated_at=source.updated_at,
            last_refresh_at=source.last_refresh_at,
            next_refresh_at=source.next_refresh_at,
            last_error=redact_text(source.last_error) if source.last_error else None,
            channel_count=source_status.channel_count if source_status else 0,
            group_count=source_status.group_count if source_status else 0,
            active_job=self._job_response(active_job) if active_job else None,
        )

    def _job_response(self, job: PlaylistImportJob) -> PlaylistImportJobResponse:
        return PlaylistImportJobResponse(
            id=job.id,
            source_id=job.source_id,
            playlist_import_id=job.playlist_import_id,
            status=cast(ImportJobState, job.status),
            progress_percent=job.progress_percent,
            message=redact_text(job.message),
            started_at=job.started_at,
            completed_at=job.completed_at,
            failure_reason=redact_text(job.failure_reason) if job.failure_reason else None,
        )

    def _import_history_item(
        self,
        playlist_import: PlaylistImport,
        source: Source,
    ) -> PlaylistImportHistoryItem:
        return PlaylistImportHistoryItem(
            id=playlist_import.id,
            source_id=playlist_import.source_id,
            source_name=source.name,
            source_kind=cast(SourceType, playlist_import.source_kind),
            status=cast(PlaylistImportState, playlist_import.status),
            started_at=playlist_import.started_at,
            completed_at=playlist_import.completed_at,
            duration_ms=playlist_import.duration_ms,
            channel_count=playlist_import.channel_count,
            group_count=playlist_import.group_count,
            warning_count=playlist_import.warning_count,
            failure_count=playlist_import.failure_count,
            warnings=[redact_text(item) for item in playlist_import.warnings_json],
            failures=[redact_text(item) for item in playlist_import.failures_json],
            failure_reason=redact_text(playlist_import.failure_reason)
            if playlist_import.failure_reason
            else None,
            checksum=playlist_import.checksum,
            source_version=playlist_import.source_version,
        )

    def _validation_response(
        self,
        parse_result: M3uParseResult,
        *,
        reachable: bool,
        extra_warnings: list[str],
        selected_content_types: set[ContentType],
        requested_content_types: set[ContentType],
    ) -> SourceValidationResponse:
        errors = parse_result.failures if not parse_result.selected_entry_count else []
        warnings = [
            *extra_warnings,
            *self._validation_warnings(parse_result, selected_content_types, requested_content_types),
        ]
        return SourceValidationResponse(
            playlist_reachable=reachable and not errors,
            channel_count=parse_result.selected_entry_count,
            total_entry_count=parse_result.total_entry_count,
            selected_entry_count=parse_result.selected_entry_count,
            excluded_entry_count=parse_result.excluded_count,
            group_count=parse_result.group_count,
            content_counts=parse_result.content_counts.as_dict(),
            selected_content_types=sorted(selected_content_types),
            deferred_content_types=self._deferred_content_types(requested_content_types),
            estimated_import_time_seconds=self._estimate_import_seconds(parse_result.selected_entry_count),
            estimated_database_rows=parse_result.selected_entry_count,
            estimated_database_bytes=self._estimate_database_bytes(parse_result.selected_entry_count),
            requires_confirmation=parse_result.total_entry_count
            > self.settings.source_import_confirmation_threshold_entries,
            confirmation_threshold_entries=self.settings.source_import_confirmation_threshold_entries,
            metadata_samples=[
                {
                    "line_number": sample.line_number,
                    "name": sample.name,
                    "group": sample.group,
                    "tvg_id": sample.tvg_id,
                    "tvg_name": sample.tvg_name,
                    "content_type": sample.content_type,
                }
                for sample in parse_result.samples
            ],
            warnings=warnings + parse_result.failures,
            errors=errors,
            checksum=parse_result.checksum,
            source_version=f"sha256:{parse_result.checksum[:12]}",
        )

    def _validation_warnings(
        self,
        parse_result: M3uParseResult,
        selected_content_types: set[ContentType],
        requested_content_types: set[ContentType],
    ) -> list[str]:
        warnings = list(parse_result.warnings)
        if parse_result.total_entry_count > self.settings.source_large_playlist_warning_entries:
            warnings.append(
                "Playlist is unusually large. Review content-type counts and confirm before importing."
            )
        if parse_result.total_entry_count > self.settings.source_import_confirmation_threshold_entries:
            warnings.append(
                "Import requires explicit administrator confirmation because the playlist exceeds "
                f"{self.settings.source_import_confirmation_threshold_entries:,} entries."
            )
        estimated_seconds = self._estimate_import_seconds(parse_result.selected_entry_count)
        if estimated_seconds > 3600:
            warnings.append(
                "Estimated import time exceeds one hour. Consider narrowing content-type options before importing."
            )
        if parse_result.excluded_count:
            selected_labels = ", ".join(
                CONTENT_TYPE_LABELS[item] for item in sorted(selected_content_types)
            ) or "none"
            warnings.append(
                f"{parse_result.excluded_count:,} entries are excluded by the selected import options "
                f"({selected_labels}). Excluded entries are counted but not stored as RawChannel rows."
            )
        if parse_result.total_entry_count and not parse_result.selected_entry_count:
            warnings.append("No entries match the selected import options; no RawChannel rows will be inserted.")
        deferred = self._deferred_content_types(requested_content_types)
        if deferred:
            labels = ", ".join(CONTENT_TYPE_LABELS[item] for item in deferred)
            warnings.append(
                f"{labels} storage is deferred until a safe VOD data model exists; those entries are excluded."
            )
        return warnings

    def _ensure_large_import_allowed(self, source: Source, parse_result: M3uParseResult) -> None:
        if (
            parse_result.total_entry_count > self.settings.source_import_confirmation_threshold_entries
            and not bool(source.config_json.get("large_import_confirmed", False))
        ):
            raise SourceValidationError(
                "Playlist import requires explicit administrator confirmation before processing "
                f"{parse_result.total_entry_count:,} entries."
            )

    def _ensure_import_still_active(self, source: Source) -> None:
        self.db.refresh(source)
        if source.deleted_at is not None:
            raise SourceValidationError("Playlist import was canceled because the source was deleted.")
        if not source.is_enabled:
            raise SourceValidationError("Playlist import was canceled because the source was disabled.")

    def _source_url_warnings(self, raw_url: str) -> list[str]:
        if raw_url.lower().startswith("http://"):
            return [
                "This source uses unencrypted HTTP. Credentials may be exposed in transit; use HTTPS when available."
            ]
        return []

    @staticmethod
    def _requested_content_types(values: list[ContentType] | None) -> set[ContentType]:
        requested = {value for value in values or ["live_tv"] if value in {"live_tv", "movie", "series", "unknown"}}
        return requested or {"live_tv"}

    def _enabled_content_types(self, values: list[ContentType] | None) -> set[ContentType]:
        requested = self._requested_content_types(values)
        safe_types: set[ContentType] = set()
        if "live_tv" in requested:
            safe_types.add("live_tv")
        if "unknown" in requested:
            safe_types.add("unknown")
        if safe_types or values:
            return safe_types
        return {"live_tv"}

    @staticmethod
    def _ensure_supported_content_type_selection(selected_content_types: set[ContentType]) -> None:
        if not selected_content_types:
            raise SourceValidationError(
                "Movies and Series storage is deferred until a safe VOD data model exists. "
                "Select Live TV or Unknown before importing."
            )

    def _source_enabled_content_types(self, source: Source) -> set[ContentType]:
        raw_values = source.config_json.get("enabled_content_types", ["live_tv"])
        if not isinstance(raw_values, list):
            return {"live_tv"}
        values = [
            cast(ContentType, value)
            for value in raw_values
            if value in {"live_tv", "movie", "series", "unknown"}
        ]
        return self._enabled_content_types(values)

    @staticmethod
    def _deferred_content_types(selected_content_types: set[ContentType]) -> list[ContentType]:
        return [cast(ContentType, item) for item in ("movie", "series") if item in selected_content_types]

    def _get_active_source(self, source_id: str) -> Source:
        source = self.db.get(Source, source_id)
        if source is None or source.deleted_at is not None:
            raise SourceNotFoundError()
        return source

    def _update_job(self, job: PlaylistImportJob, progress: int, message: str) -> None:
        job.progress_percent = progress
        job.message = message
        self.db.commit()

    def _fail_job(self, job: PlaylistImportJob, message: str) -> None:
        redacted_message = redact_text(message)
        job.status = "failed"
        job.progress_percent = 100
        job.message = redacted_message
        job.failure_reason = redacted_message
        job.completed_at = utcnow()

    def _store_upload(self, filename: str, content: bytes) -> Path:
        upload_dir = Path(self.settings.source_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        stored_path = self.reserve_upload_path(filename)
        with stored_path.open("wb") as output:
            output.write(content)
        return stored_path

    def reserve_upload_path(self, filename: str) -> Path:
        upload_dir = Path(self.settings.source_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir / f"{uuid.uuid4()}-{self._safe_filename(filename)}"

    @staticmethod
    def _safe_filename(filename: str) -> str:
        candidate = Path(filename).name.strip()
        if not candidate:
            return "playlist.m3u"
        return "".join(character for character in candidate if character.isalnum() or character in {".", "-", "_"})

    def _estimate_import_seconds(self, channel_count: int) -> int:
        if channel_count <= 0:
            return 0
        return max(1, math.ceil(channel_count / self.settings.source_estimated_entries_per_second))

    @staticmethod
    def _estimate_database_bytes(channel_count: int) -> int:
        return channel_count * 2_048

    @staticmethod
    def _next_refresh_time(refresh_interval_minutes: int | None) -> datetime | None:
        if refresh_interval_minutes is None:
            return None
        return datetime.now(UTC) + timedelta(minutes=refresh_interval_minutes)

    @staticmethod
    def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
        return int((completed_at - started_at).total_seconds() * 1000)


def copy_upload_to_path(upload_file: UploadFile, destination: Path, *, max_bytes: int) -> None:
    bytes_written = 0
    with upload_file.file as source, destination.open("wb") as output:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            bytes_written += len(chunk)
            if bytes_written > max_bytes:
                destination.unlink(missing_ok=True)
                raise SourceValidationError("Uploaded playlist exceeds the configured maximum size.")
            output.write(chunk)
