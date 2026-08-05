from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from streamforge_api.domain.url_safety import SafeUrlValidator

ATTRIBUTE_PATTERN = re.compile(r"""([\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s,]+))""")


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


@dataclass(frozen=True)
class M3uParseResult:
    channels: list[M3uChannel]
    warnings: list[str]
    failures: list[str]
    checksum: str
    group_count: int


@dataclass(frozen=True)
class PendingExtInf:
    raw_line: str
    line_number: int
    duration: str | None
    attributes: dict[str, str]
    title: str


class M3uParser:
    def __init__(self, url_validator: SafeUrlValidator | None = None) -> None:
        self.url_validator = url_validator or SafeUrlValidator(allow_private_destinations=True)

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
                    failures.append(
                        f"Line {pending.line_number}: EXTINF entry is missing a stream URL."
                    )
                pending = self._parse_extinf(line, index)
                continue
            if line.startswith("#"):
                continue

            if pending is None:
                failures.append(f"Line {index}: stream URL is missing EXTINF metadata.")
                continue

            url_result = self.url_validator.validate_stream_url(line)
            if not url_result.is_safe:
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
        )

    def _parse_extinf(self, line: str, line_number: int) -> PendingExtInf:
        metadata, title = self._split_extinf(line)
        duration = self._parse_duration(metadata)
        attributes = {
            match.group(1): next(
                group for group in (match.group(2), match.group(3), match.group(4)) if group is not None
            )
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
        metadata, separator, title = remainder.partition(",")
        if not separator:
            return remainder, ""
        return metadata.strip(), title.strip()

    @staticmethod
    def _parse_duration(metadata: str) -> str | None:
        stripped = metadata.strip()
        if not stripped:
            return None
        return stripped.split(maxsplit=1)[0]
