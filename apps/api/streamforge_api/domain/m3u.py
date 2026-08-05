from __future__ import annotations

import hashlib
import re
<<<<<<< HEAD
from dataclasses import dataclass
=======
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)

from streamforge_api.domain.url_safety import SafeUrlValidator

ATTRIBUTE_PATTERN = re.compile(r"""([\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s,]+))""")
<<<<<<< HEAD
=======
SERIES_EPISODE_PATTERN = re.compile(r"\bS\d{1,2}\s*E\d{1,3}\b", re.IGNORECASE)

ContentType = Literal["live_tv", "movie", "series", "unknown"]

CONTENT_TYPE_LABELS: dict[ContentType, str] = {
    "live_tv": "Live TV",
    "movie": "Movie",
    "series": "Series Episode",
    "unknown": "Unknown",
}
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)


@dataclass(frozen=True)
class M3uChannel:
    original_name: str
    original_url: str
    original_group: str | None
    original_tvg_id: str | None
    original_tvg_name: str | None
    original_logo_url: str | None
    attributes: dict[str, str]
    raw_extinf: str
    line_number: int
    duration: str | None
<<<<<<< HEAD
=======
    content_type: ContentType


@dataclass(frozen=True)
class MetadataSample:
    line_number: int
    name: str
    group: str | None
    tvg_id: str | None
    tvg_name: str | None
    content_type: ContentType


@dataclass(frozen=True)
class ContentCounts:
    live_tv: int = 0
    movie: int = 0
    series: int = 0
    unknown: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "live_tv": self.live_tv,
            "movie": self.movie,
            "series": self.series,
            "unknown": self.unknown,
        }
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)


@dataclass(frozen=True)
class M3uParseResult:
    channels: list[M3uChannel]
    warnings: list[str]
    failures: list[str]
    checksum: str
    group_count: int
<<<<<<< HEAD
=======
    total_entry_count: int
    selected_entry_count: int
    content_counts: ContentCounts
    excluded_count: int
    samples: list[MetadataSample]
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)


@dataclass(frozen=True)
class PendingExtInf:
    raw_line: str
    line_number: int
    duration: str | None
    attributes: dict[str, str]
    title: str


<<<<<<< HEAD
=======
@dataclass
class ParseAccumulator:
    channels: list[M3uChannel] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    groups: set[str] = field(default_factory=set)
    samples: list[MetadataSample] = field(default_factory=list)
    total_entry_count: int = 0
    selected_entry_count: int = 0
    live_tv_count: int = 0
    movie_count: int = 0
    series_count: int = 0
    unknown_count: int = 0

    def count_content_type(self, content_type: ContentType) -> None:
        if content_type == "live_tv":
            self.live_tv_count += 1
        elif content_type == "movie":
            self.movie_count += 1
        elif content_type == "series":
            self.series_count += 1
        else:
            self.unknown_count += 1

    @property
    def content_counts(self) -> ContentCounts:
        return ContentCounts(
            live_tv=self.live_tv_count,
            movie=self.movie_count,
            series=self.series_count,
            unknown=self.unknown_count,
        )


>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
class M3uParser:
    def __init__(self, url_validator: SafeUrlValidator | None = None) -> None:
        self.url_validator = url_validator or SafeUrlValidator(allow_private_destinations=True)

<<<<<<< HEAD
    def parse_bytes(self, playlist_bytes: bytes) -> M3uParseResult:
        checksum = hashlib.sha256(playlist_bytes).hexdigest()
        text = playlist_bytes.decode("utf-8-sig", errors="replace")
        return self.parse_text(text, checksum=checksum)

    def parse_text(self, playlist_text: str, *, checksum: str | None = None) -> M3uParseResult:
        normalized_checksum = checksum or hashlib.sha256(playlist_text.encode("utf-8")).hexdigest()
        channels: list[M3uChannel] = []
        warnings: list[str] = []
        failures: list[str] = []
        pending: PendingExtInf | None = None
        has_header = False

        for index, raw_line in enumerate(playlist_text.splitlines(), start=1):
=======
    def parse_bytes(
        self,
        playlist_bytes: bytes,
        *,
        include_content_types: set[ContentType] | None = None,
        sample_limit: int = 5,
        keep_channels: bool = True,
    ) -> M3uParseResult:
        checksum = hashlib.sha256(playlist_bytes).hexdigest()
        text = playlist_bytes.decode("utf-8-sig", errors="replace")
        return self.parse_text(
            text,
            checksum=checksum,
            include_content_types=include_content_types,
            sample_limit=sample_limit,
            keep_channels=keep_channels,
        )

    def parse_path(
        self,
        path: Path,
        *,
        include_content_types: set[ContentType] | None = None,
        sample_limit: int = 5,
        keep_channels: bool = True,
    ) -> M3uParseResult:
        checksum = self.checksum_path(path)
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as input_file:
            return self.parse_lines(
                input_file,
            checksum=checksum,
            include_content_types=include_content_types,
            sample_limit=sample_limit,
            keep_channels=keep_channels,
        )

    def parse_text(
        self,
        playlist_text: str,
        *,
        checksum: str | None = None,
        include_content_types: set[ContentType] | None = None,
        sample_limit: int = 5,
        keep_channels: bool = True,
    ) -> M3uParseResult:
        normalized_checksum = checksum or hashlib.sha256(playlist_text.encode("utf-8")).hexdigest()
        return self.parse_lines(
            playlist_text.splitlines(),
            checksum=normalized_checksum,
            include_content_types=include_content_types,
            sample_limit=sample_limit,
            keep_channels=keep_channels,
        )

    def parse_lines(
        self,
        lines: Iterable[str],
        *,
        checksum: str,
        include_content_types: set[ContentType] | None = None,
        sample_limit: int = 5,
        keep_channels: bool = True,
    ) -> M3uParseResult:
        accumulator = ParseAccumulator()
        pending: PendingExtInf | None = None
        has_header = False

        for index, raw_line in enumerate(lines, start=1):
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
            line = raw_line.strip()
            if index == 1:
                line = line.removeprefix("\ufeff")
            if not line:
                continue
            upper_line = line.upper()
            if upper_line.startswith("#EXTM3U"):
                has_header = True
                continue
            if upper_line.startswith("#EXTINF"):
                if pending is not None:
<<<<<<< HEAD
                    failures.append(
=======
                    accumulator.failures.append(
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
                        f"Line {pending.line_number}: EXTINF entry is missing a stream URL."
                    )
                pending = self._parse_extinf(line, index)
                continue
            if line.startswith("#"):
                continue

            if pending is None:
<<<<<<< HEAD
                failures.append(f"Line {index}: stream URL is missing EXTINF metadata.")
=======
                accumulator.failures.append(f"Line {index}: stream URL is missing EXTINF metadata.")
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
                continue

            url_result = self.url_validator.validate_stream_url(line)
            if not url_result.is_safe:
<<<<<<< HEAD
                failures.append(f"Line {index}: {' '.join(url_result.errors)}")
                pending = None
                continue

            channel_name = pending.title or pending.attributes.get("tvg-name") or ""
            if not channel_name:
                failures.append(f"Line {pending.line_number}: EXTINF entry is missing a channel name.")
                pending = None
                continue

            channels.append(
                M3uChannel(
                    original_name=channel_name,
                    original_url=line,
                    original_group=pending.attributes.get("group-title"),
                    original_tvg_id=pending.attributes.get("tvg-id"),
                    original_tvg_name=pending.attributes.get("tvg-name"),
                    original_logo_url=pending.attributes.get("tvg-logo"),
                    attributes=pending.attributes,
                    raw_extinf=pending.raw_line,
                    line_number=pending.line_number,
                    duration=pending.duration,
                )
            )
            pending = None

        if pending is not None:
            failures.append(f"Line {pending.line_number}: EXTINF entry is missing a stream URL.")
        if not has_header:
            warnings.append("Playlist does not include an #EXTM3U header.")
        if not channels:
            failures.append("No playable channel entries were found.")

        group_count = len({channel.original_group for channel in channels if channel.original_group})
        return M3uParseResult(
            channels=channels,
            warnings=warnings,
            failures=failures,
            checksum=normalized_checksum,
            group_count=group_count,
=======
                accumulator.failures.append(f"Line {index}: {' '.join(url_result.errors)}")
                pending = None
                continue

            channel = self._channel_from_pending(pending, line)
            if channel is None:
                accumulator.failures.append(f"Line {pending.line_number}: EXTINF entry is missing a channel name.")
                pending = None
                continue

            accumulator.total_entry_count += 1
            accumulator.count_content_type(channel.content_type)
            if channel.original_group:
                accumulator.groups.add(channel.original_group)
            if len(accumulator.samples) < sample_limit:
                accumulator.samples.append(
                    MetadataSample(
                        line_number=channel.line_number,
                        name=channel.original_name,
                        group=channel.original_group,
                        tvg_id=channel.original_tvg_id,
                        tvg_name=channel.original_tvg_name,
                        content_type=channel.content_type,
                    )
                )
            if include_content_types is None or channel.content_type in include_content_types:
                accumulator.selected_entry_count += 1
                if keep_channels:
                    accumulator.channels.append(channel)
            pending = None

        if pending is not None:
            accumulator.failures.append(f"Line {pending.line_number}: EXTINF entry is missing a stream URL.")
        if not has_header:
            accumulator.warnings.append("Playlist does not include an #EXTM3U header.")
        if accumulator.total_entry_count == 0:
            accumulator.failures.append("No playable playlist entries were found.")

        excluded_count = accumulator.total_entry_count - accumulator.selected_entry_count
        return M3uParseResult(
            channels=accumulator.channels,
            warnings=accumulator.warnings,
            failures=accumulator.failures,
            checksum=checksum,
            group_count=len(accumulator.groups),
            total_entry_count=accumulator.total_entry_count,
            selected_entry_count=accumulator.selected_entry_count,
            content_counts=accumulator.content_counts,
            excluded_count=excluded_count,
            samples=accumulator.samples,
        )

    def iter_channels_path(
        self,
        path: Path,
        *,
        include_content_types: set[ContentType],
    ) -> Iterable[M3uChannel]:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as input_file:
            yield from self.iter_channels(input_file, include_content_types=include_content_types)

    def iter_channels(
        self,
        lines: Iterable[str],
        *,
        include_content_types: set[ContentType],
    ) -> Iterable[M3uChannel]:
        pending: PendingExtInf | None = None
        for index, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if index == 1:
                line = line.removeprefix("\ufeff")
            upper_line = line.upper()
            if not line or upper_line.startswith("#EXTM3U"):
                continue
            if upper_line.startswith("#EXTINF"):
                pending = self._parse_extinf(line, index)
                continue
            if line.startswith("#") or pending is None:
                continue
            url_result = self.url_validator.validate_stream_url(line)
            if not url_result.is_safe:
                pending = None
                continue
            channel = self._channel_from_pending(pending, line)
            pending = None
            if channel is not None and channel.content_type in include_content_types:
                yield channel

    def _channel_from_pending(
        self,
        pending: PendingExtInf,
        stream_url: str,
    ) -> M3uChannel | None:
        channel_name = pending.title or pending.attributes.get("tvg-name") or ""
        if not channel_name:
            return None

        group = (
            pending.attributes.get("group-title")
            or pending.attributes.get("group_title")
            or pending.attributes.get("group")
        )
        content_type = classify_content_type(
            channel_name=channel_name,
            group=group,
            stream_url=stream_url,
            attributes=pending.attributes,
        )
        return M3uChannel(
            original_name=channel_name,
            original_url=stream_url,
            original_group=group,
            original_tvg_id=pending.attributes.get("tvg-id"),
            original_tvg_name=pending.attributes.get("tvg-name"),
            original_logo_url=pending.attributes.get("tvg-logo"),
            attributes=pending.attributes,
            raw_extinf=pending.raw_line,
            line_number=pending.line_number,
            duration=pending.duration,
            content_type=content_type,
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
        )

    def _parse_extinf(self, line: str, line_number: int) -> PendingExtInf:
        metadata, title = self._split_extinf(line)
        duration = self._parse_duration(metadata)
        attributes = {
<<<<<<< HEAD
            match.group(1): next(
                group for group in (match.group(2), match.group(3), match.group(4)) if group is not None
            )
=======
            match.group(1).lower(): next(
                group for group in (match.group(2), match.group(3), match.group(4)) if group is not None
            ).strip()
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
            for match in ATTRIBUTE_PATTERN.finditer(metadata)
        }
        return PendingExtInf(
            raw_line=line,
            line_number=line_number,
            duration=duration,
            attributes=attributes,
            title=title,
        )

    @staticmethod
    def _split_extinf(line: str) -> tuple[str, str]:
        _, _, remainder = line.partition(":")
<<<<<<< HEAD
        metadata, separator, title = remainder.partition(",")
        if not separator:
            return remainder, ""
        return metadata.strip(), title.strip()
=======
        quote_character: str | None = None
        for index, character in enumerate(remainder):
            if character in {"'", '"'}:
                if quote_character == character:
                    quote_character = None
                elif quote_character is None:
                    quote_character = character
            elif character == "," and quote_character is None:
                return remainder[:index].strip(), remainder[index + 1 :].strip()
        return remainder.strip(), ""
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)

    @staticmethod
    def _parse_duration(metadata: str) -> str | None:
        stripped = metadata.strip()
        if not stripped:
            return None
        return stripped.split(maxsplit=1)[0]
<<<<<<< HEAD
=======

    @staticmethod
    def checksum_path(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as input_file:
            for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


def classify_content_type(
    *,
    channel_name: str,
    group: str | None,
    stream_url: str,
    attributes: dict[str, str],
) -> ContentType:
    haystack = " ".join(
        part
        for part in (
            channel_name,
            group or "",
            stream_url,
            attributes.get("tvg-id", ""),
            attributes.get("tvg-name", ""),
        )
        if part
    ).lower()

    if SERIES_EPISODE_PATTERN.search(haystack) or any(
        marker in haystack for marker in ("/series/", "/show/", "/shows/", " series ", " tv series ")
    ):
        return "series"
    if any(marker in haystack for marker in ("/movie/", "/movies/", "/vod/", " movie ", " movies ", " vod ")):
        return "movie"
    if any(
        marker in haystack
        for marker in (
            "/live/",
            "/channel/",
            "/channels/",
            ".m3u8",
            " live ",
            " news",
            " sports",
            " local",
        )
    ):
        return "live_tv"
    return "unknown"
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
