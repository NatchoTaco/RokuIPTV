from __future__ import annotations

import hashlib
import math
import socket
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from fastapi import UploadFile
import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from streamforge_api.core.config import Settings
from streamforge_api.core.errors import (
    ImportJobNotFoundError,
    SourceDisabledError,
    SourceNotFoundError,
    SourceValidationError,
)
from streamforge_api.core.secrets import SecretBox
from streamforge_api.domain.m3u import M3uChannel, M3uParseResult, M3uParser
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
    content: bytes
    source_version: str


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

    def validate_url_source(self, raw_url: str) -> SourceValidationResponse:
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
        try:
            playlist = self._fetch_remote_playlist(url_result.normalized_url)
        except SourceValidationError as exc:
            return SourceValidationResponse(
                playlist_reachable=False,
                channel_count=0,
                group_count=0,
                estimated_import_time_seconds=0,
                warnings=[],
                errors=[exc.public_message],
            )
        return self._validation_response(self.parser.parse_bytes(playlist.content), reachable=True)

    def validate_uploaded_playlist(self, content: bytes) -> SourceValidationResponse:
        if len(content) > self.settings.source_max_playlist_bytes:
            return SourceValidationResponse(
                playlist_reachable=False,
                channel_count=0,
                group_count=0,
                estimated_import_time_seconds=0,
                warnings=[],
                errors=["Uploaded playlist exceeds the configured maximum size."],
            )
        return self._validation_response(self.parser.parse_bytes(content), reachable=True)

    def create_url_source(
        self,
        *,
        name: str,
        raw_url: str,
        refresh_interval_minutes: int | None,
        actor: User,
    ) -> SourceCreatedResponse:
        url_result = self.url_validator.validate_source_url(raw_url, resolve_dns=False)
        if not url_result.is_safe or url_result.normalized_url is None:
            raise SourceValidationError(" ".join(url_result.errors))
        next_refresh_at = self._next_refresh_time(refresh_interval_minutes)
        source = Source(
            name=name.strip(),
            source_type="m3u_url",
            status="importing",
            config_json={
                "display_location": url_result.display_url,
                "refresh_interval_minutes": refresh_interval_minutes,
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
        actor: User,
    ) -> SourceCreatedResponse:
        validation = self.validate_uploaded_playlist(content)
        if not validation.playlist_reachable:
            raise SourceValidationError(" ".join(validation.errors))
        stored_path = self._store_upload(filename, content)
        source = Source(
            name=name.strip(),
            source_type="m3u_upload",
            status="importing",
            config_json={
                "display_location": self._safe_filename(filename),
                "upload_filename": self._safe_filename(filename),
                "refresh_interval_minutes": refresh_interval_minutes,
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
        actor: User,
    ) -> SourceCreatedResponse:
        source = Source(
            name=name.strip(),
            source_type="demo_playlist",
            status="importing",
            config_json={
                "display_location": "Built-in synthetic playlist",
                "refresh_interval_minutes": refresh_interval_minutes,
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

    def update_source(self, source_id: str, *, is_enabled: bool | None, refresh_interval_minutes: int | None) -> SourceSummaryResponse:
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
        self.db.commit()

        try:
            loaded_playlist = self._load_playlist(source)
            self._update_job(job, 25, "Playlist loaded.")
            parse_result = self.parser.parse_bytes(loaded_playlist.content)
            self._update_job(job, 50, "Playlist parsed.")
            if not parse_result.channels:
                raise SourceValidationError("No playable channel entries were found.")
            self._store_raw_channels(source, playlist_import, parse_result.channels)
            self._update_job(job, 90, "Raw channels stored.")

            completed_at = utcnow()
            duration_ms = self._duration_ms(started_at, completed_at)
            import_status = "warning" if parse_result.warnings or parse_result.failures else "completed"
            playlist_import.status = import_status
            playlist_import.completed_at = completed_at
            playlist_import.duration_ms = duration_ms
            playlist_import.channel_count = len(parse_result.channels)
            playlist_import.group_count = parse_result.group_count
            playlist_import.warning_count = len(parse_result.warnings)
            playlist_import.failure_count = len(parse_result.failures)
            playlist_import.warnings_json = parse_result.warnings
            playlist_import.failures_json = parse_result.failures
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
                channel_count=len(parse_result.channels),
                group_count=parse_result.group_count,
                checked_at=completed_at,
            )
            job.status = "succeeded"
            job.progress_percent = 100
            job.message = status_message
            job.completed_at = completed_at
        except Exception as exc:
            completed_at = utcnow()
            public_message = str(exc) or "Playlist import failed."
            playlist_import.status = "failed"
            playlist_import.completed_at = completed_at
            playlist_import.duration_ms = self._duration_ms(started_at, completed_at)
            playlist_import.failure_reason = public_message
            playlist_import.failures_json = [public_message]
            playlist_import.failure_count = 1
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
        self.db.commit()
        return self._job_response(job)

    def _load_playlist(self, source: Source) -> LoadedPlaylist:
        if source.source_type == "demo_playlist":
            demo_path = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_demo_playlist.m3u"
            content = demo_path.read_bytes()
            checksum = hashlib.sha256(content).hexdigest()
            return LoadedPlaylist(content=content, source_version=f"sha256:{checksum[:12]}")

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
            content = resolved_path.read_bytes()
            if len(content) > self.settings.source_max_playlist_bytes:
                raise SourceValidationError("Uploaded playlist exceeds the configured maximum size.")
            checksum = hashlib.sha256(content).hexdigest()
            return LoadedPlaylist(content=content, source_version=f"sha256:{checksum[:12]}")
        raise SourceValidationError("Unsupported source type.")

    def _fetch_remote_playlist(self, raw_url: str) -> LoadedPlaylist:
        current_url = raw_url
        headers = {"User-Agent": "StreamForge/0.1 playlist-validator"}
        with httpx.Client(timeout=self.settings.source_request_timeout_seconds, headers=headers) as client:
            for _redirect in range(5):
                url_result = self.url_validator.validate_source_url(current_url)
                if not url_result.is_safe or url_result.normalized_url is None:
                    raise SourceValidationError(" ".join(url_result.errors))
                try:
                    response = client.get(url_result.normalized_url, follow_redirects=False)
                except httpx.TimeoutException as exc:
                    raise SourceValidationError("Playlist request timed out.") from exc
                except httpx.HTTPError as exc:
                    raise SourceValidationError("Playlist could not be reached.") from exc

                if response.is_redirect:
                    redirect_url = response.headers.get("location")
                    if not redirect_url:
                        raise SourceValidationError("Playlist redirected without a destination.")
                    current_url = str(httpx.URL(url_result.normalized_url).join(redirect_url))
                    continue
                if response.status_code >= 400:
                    raise SourceValidationError(f"Playlist returned HTTP {response.status_code}.")
                content = response.content
                if len(content) > self.settings.source_max_playlist_bytes:
                    raise SourceValidationError("Playlist exceeds the configured maximum size.")
                checksum = hashlib.sha256(content).hexdigest()
                return LoadedPlaylist(content=content, source_version=f"sha256:{checksum[:12]}")
        raise SourceValidationError("Playlist redirected too many times.")

    def _store_raw_channels(
        self,
        source: Source,
        playlist_import: PlaylistImport,
        channels: list[M3uChannel],
    ) -> None:
        for channel in channels:
            self.db.add(
                RawChannel(
                    source_id=source.id,
                    playlist_import_id=playlist_import.id,
                    original_name=channel.original_name,
                    original_group=channel.original_group,
                    original_url=channel.original_url,
                    original_tvg_id=channel.original_tvg_id,
                    original_tvg_name=channel.original_tvg_name,
                    original_logo_url=channel.original_logo_url,
                    source_metadata_json={
                        "duration": channel.duration,
                    },
                    line_number=channel.line_number,
                    raw_extinf=channel.raw_extinf,
                    raw_attributes_json=channel.attributes,
                    url_checksum=hashlib.sha256(channel.original_url.encode("utf-8")).hexdigest(),
                )
            )

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
        source_status.message = message
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
            status_message=source_status.message if source_status else "Source has not been imported yet.",
            display_location=str(source.config_json.get("display_location", "Hidden")),
            is_enabled=source.is_enabled,
            refresh_interval_minutes=source.refresh_interval_minutes,
            last_updated_at=source.updated_at,
            last_refresh_at=source.last_refresh_at,
            next_refresh_at=source.next_refresh_at,
            last_error=source.last_error,
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
            message=job.message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            failure_reason=job.failure_reason,
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
            warnings=playlist_import.warnings_json,
            failures=playlist_import.failures_json,
            failure_reason=playlist_import.failure_reason,
            checksum=playlist_import.checksum,
            source_version=playlist_import.source_version,
        )

    def _validation_response(
        self,
        parse_result: M3uParseResult,
        *,
        reachable: bool,
    ) -> SourceValidationResponse:
        errors = parse_result.failures if not parse_result.channels else []
        return SourceValidationResponse(
            playlist_reachable=reachable and not errors,
            channel_count=len(parse_result.channels),
            group_count=parse_result.group_count,
            estimated_import_time_seconds=self._estimate_import_seconds(len(parse_result.channels)),
            warnings=parse_result.warnings + parse_result.failures,
            errors=errors,
            checksum=parse_result.checksum,
            source_version=f"sha256:{parse_result.checksum[:12]}",
        )

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
        job.status = "failed"
        job.progress_percent = 100
        job.message = message
        job.failure_reason = message
        job.completed_at = utcnow()

    def _store_upload(self, filename: str, content: bytes) -> Path:
        upload_dir = Path(self.settings.source_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._safe_filename(filename)
        stored_path = upload_dir / f"{uuid.uuid4()}-{safe_name}"
        with stored_path.open("wb") as output:
            output.write(content)
        return stored_path

    @staticmethod
    def _safe_filename(filename: str) -> str:
        candidate = Path(filename).name.strip()
        if not candidate:
            return "playlist.m3u"
        return "".join(character for character in candidate if character.isalnum() or character in {".", "-", "_"})

    @staticmethod
    def _estimate_import_seconds(channel_count: int) -> int:
        if channel_count <= 0:
            return 0
        return max(1, math.ceil(channel_count / 250))

    @staticmethod
    def _next_refresh_time(refresh_interval_minutes: int | None) -> datetime | None:
        if refresh_interval_minutes is None:
            return None
        return datetime.now(UTC) + timedelta(minutes=refresh_interval_minutes)

    @staticmethod
    def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
        return int((completed_at - started_at).total_seconds() * 1000)


def copy_upload_to_bytes(upload_file: UploadFile, *, max_bytes: int) -> bytes:
    with upload_file.file as source:
        limited_reader = source.read(max_bytes + 1)
        if len(limited_reader) > max_bytes:
            raise SourceValidationError("Uploaded playlist exceeds the configured maximum size.")
        return limited_reader
