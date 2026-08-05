from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

ContentType = Literal["live_tv", "movie", "series", "unknown"]
FilterProfile = Literal["light", "recommended", "aggressive", "custom"]
FilterAction = Literal["allow", "hide", "review"]

STANDARD_GROUPS: tuple[str, ...] = (
    "Local",
    "News",
    "Sports",
    "Entertainment",
    "Movies",
    "Kids",
    "Documentary",
    "Lifestyle",
    "Music",
    "Weather",
    "International",
    "Events",
    "Religious",
    "Shopping",
    "Adult",
    "Other",
)

GENERIC_GROUPS = {
    "all",
    "channel",
    "channels",
    "general",
    "live",
    "live tv",
    "tv",
    "unknown",
}

COUNTRY_ALIASES: dict[str, tuple[str, ...]] = {
    "United States": ("us", "usa", "u.s.", "united states"),
    "United Kingdom": ("uk", "gb", "britain", "united kingdom"),
    "Canada": ("ca", "canada"),
    "Australia": ("au", "australia"),
    "France": ("fr", "france"),
    "Germany": ("de", "germany"),
    "Spain": ("es", "spain"),
    "Italy": ("it", "italy"),
    "Mexico": ("mx", "mexico"),
}

LANGUAGE_ALIASES: dict[str, tuple[str, ...]] = {
    "English": ("english", "eng", "usa", "us", "uk", "ca", "au"),
    "Spanish": ("spanish", "espanol", "español", "latino", "mx", "es"),
    "French": ("french", "français", "francais", "fr"),
    "German": ("german", "deutsch", "de"),
    "Italian": ("italian", "italiano", "it"),
    "Portuguese": ("portuguese", "portugues", "brasil", "brazil", "pt", "br"),
    "Arabic": ("arabic", "العربية", "ar"),
}

QUALITY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("4K", r"\b(?:4k|uhd|2160p)\b"),
    ("FHD", r"\b(?:fhd|full\s*hd|1080p)\b"),
    ("HD", r"\b(?:hd|720p)\b"),
    ("SD", r"\b(?:sd|480p|360p)\b"),
    ("60 FPS", r"\b(?:60\s*fps|60fps)\b"),
    ("50 FPS", r"\b(?:50\s*fps|50fps)\b"),
)

GROUP_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Adult", ("xxx", "adult", "porn", "18+")),
    ("Shopping", ("shopping", "shop", "qvc", "hsn")),
    ("Religious", ("religious", "faith", "church", "gospel", "god tv")),
    ("News", ("news", "cnn", "fox news", "msnbc", "bbc world", "cnbc", "sky news")),
    ("Sports", ("sport", "espn", "nba", "nfl", "mlb", "nhl", "soccer", "football")),
    ("Kids", ("kids", "children", "cartoon", "nick", "disney junior")),
    ("Documentary", ("documentary", "docs", "history", "nat geo", "discovery")),
    ("Weather", ("weather", "radar")),
    ("Music", ("music", "mtv", "vh1", "radio")),
    ("Events", ("event", "ppv", "pay per view")),
    ("Movies", ("movie", "cinema", "film")),
    ("Lifestyle", ("food", "travel", "home", "garden", "lifestyle", "cooking")),
    ("International", ("international", "latino", "spanish", "french", "arabic", "world")),
    ("Local", ("local", "abc", "cbs", "nbc", "pbs", "cw", "fox ")),
)

PROVIDER_PREFIX_PATTERN = re.compile(
    r"^\s*(?:\[(?P<bracket>[a-z]{2,3})\]|(?P<prefix>[a-z]{2,3}))\s*(?:[:|/\-•]+|\s{2,})\s*",
    re.IGNORECASE,
)
QUALITY_SUFFIX_PATTERN = re.compile(
    r"(?:\s*[-|:/•]?\s*[\[(]?\s*(?:uhd|4k|fhd|full\s*hd|hd|sd|2160p|1080p|720p|480p|360p|"
    r"hevc|h\.?265|50\s*fps|60\s*fps|50fps|60fps)\s*[\])]?\s*)+$",
    re.IGNORECASE,
)
NOISE_SUFFIX_PATTERN = re.compile(
    r"(?:\s*[-|:/•]?\s*(?:backup|back\s*up|test|raw\s*feed|feed|vip|new|alt|alternate)\s*\d*)+$",
    re.IGNORECASE,
)
TOKEN_SPLIT_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class NormalizationResult:
    display_name: str
    normalized_key: str
    group_name: str
    group_key: str
    country: str | None
    language: str | None
    category: str
    content_type: ContentType
    quality: str | None
    flags: tuple[str, ...]
    explanations: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class FilterEvaluation:
    action: FilterAction
    visibility_status: str
    reasons: tuple[str, ...]
    explanations: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class DuplicateEvaluation:
    confidence: float
    reasons: tuple[str, ...]
    safe_to_cluster: bool


def normalize_channel(
    *,
    original_name: str,
    original_group: str | None,
    source_content_type: str | None,
    stream_url: str,
    attributes: dict[str, str],
) -> NormalizationResult:
    name = normalize_unicode(original_name).strip()
    group = normalize_unicode(original_group or "").strip() or None
    haystack = " ".join(
        part
        for part in (
            name,
            group or "",
            attributes.get("tvg-id", ""),
            attributes.get("tvg-name", ""),
            stream_url,
        )
        if part
    )
    explanations: list[dict[str, str]] = []

    country = infer_country(name=name, group=group)
    if country:
        explanations.append({"field": "country", "reason": f"Inferred {country} from name or group prefix."})

    display_name = strip_provider_prefix(name)
    if display_name != name:
        explanations.append({"field": "name", "reason": "Removed provider country/prefix decoration."})

    without_noise = NOISE_SUFFIX_PATTERN.sub("", display_name).strip()
    flags = set(infer_flags(haystack, None))
    if without_noise != display_name:
        flags.add("test_backup")
        explanations.append({"field": "name", "reason": "Removed provider test/backup/feed suffix."})
    display_name = without_noise or display_name

    quality = infer_quality(haystack)
    if quality:
        display_name = QUALITY_SUFFIX_PATTERN.sub("", display_name).strip()
        flags.update(infer_flags(haystack, quality))
        explanations.append({"field": "quality", "reason": f"Detected provider quality label {quality}."})

    without_noise = NOISE_SUFFIX_PATTERN.sub("", display_name).strip()
    if without_noise != display_name:
        flags.add("test_backup")
        explanations.append({"field": "name", "reason": "Removed provider test/backup/feed suffix."})
    display_name = cleanup_display_name(without_noise or display_name or name)
    if not display_name:
        display_name = "Unnamed Channel"
        flags.add("missing_name")
        explanations.append({"field": "name", "reason": "Missing or malformed name was replaced for display."})

    language = infer_language(name=name, group=group)
    if language and language != "English":
        flags.add("foreign_language")
        explanations.append({"field": "language", "reason": f"Inferred {language} from provider metadata."})
    elif language:
        explanations.append({"field": "language", "reason": "Inferred English from region metadata."})

    category = infer_group(name=display_name, original_group=group, haystack=haystack)
    if group is None or normalize_key(group) in GENERIC_GROUPS:
        explanations.append({"field": "group", "reason": f"Inferred standard group {category} without usable group-title."})
    else:
        explanations.append({"field": "group", "reason": f"Mapped provider group {group} to {category}."})

    content_type = infer_content_type(
        source_content_type=source_content_type,
        name=display_name,
        group=group,
        stream_url=stream_url,
        haystack=haystack,
    )
    explanations.append({"field": "content_type", "reason": f"Classified as {content_type}."})

    normalized_key = normalize_key(display_name)
    if not normalized_key:
        normalized_key = "unnamed-channel"

    return NormalizationResult(
        display_name=display_name,
        normalized_key=normalized_key,
        group_name=category,
        group_key=normalize_key(category),
        country=country,
        language=language,
        category=category,
        content_type=content_type,
        quality=quality,
        flags=tuple(sorted(flags)),
        explanations=tuple(explanations),
    )


def evaluate_filter(
    result: NormalizationResult,
    *,
    profile: FilterProfile,
    manual_visibility_status: str | None,
) -> FilterEvaluation:
    explanations: list[dict[str, str]] = []
    if manual_visibility_status == "always_visible":
        return FilterEvaluation(
            action="allow",
            visibility_status="always_visible",
            reasons=("allowlist override",),
            explanations=(
                {
                    "rule": "allowlist",
                    "reason": "Manual allowlist protection overrides automatic filtering.",
                },
            ),
        )
    if manual_visibility_status == "hidden":
        return FilterEvaluation(
            action="hide",
            visibility_status="hidden",
            reasons=("manual blocklist",),
            explanations=({"rule": "manual_blocklist", "reason": "Channel was manually hidden."},),
        )

    reasons = automatic_filter_reasons(result, profile)
    if reasons:
        explanations.append(
            {
                "rule": f"{profile}_profile",
                "reason": "Matched automatic cleanup criteria: " + ", ".join(reasons),
            }
        )
        return FilterEvaluation(
            action="hide",
            visibility_status="hidden",
            reasons=tuple(reasons),
            explanations=tuple(explanations),
        )

    return FilterEvaluation(
        action="allow",
        visibility_status="visible",
        reasons=("visible by profile",),
        explanations=(
            {
                "rule": f"{profile}_profile",
                "reason": "No automatic hide criteria matched.",
            },
        ),
    )


def automatic_filter_reasons(result: NormalizationResult, profile: FilterProfile) -> list[str]:
    if profile == "custom":
        return []

    reasons: list[str] = []
    if "missing_name" in result.flags:
        reasons.append("missing or malformed name")
    if "adult" in result.flags:
        reasons.append("suspected adult content")
    if profile in {"recommended", "aggressive"} and "test_backup" in result.flags:
        reasons.append("test or backup stream")
    if profile == "aggressive":
        aggressive_flags = {
            "shopping": "shopping channel",
            "religious": "religious channel",
            "foreign_language": "foreign-language channel",
            "loop_24_7": "24/7 loop",
            "low_quality": "low-quality stream",
        }
        reasons.extend(reason for flag, reason in aggressive_flags.items() if flag in result.flags)
    return reasons


def duplicate_confidence(
    *,
    left_key: str | None,
    right_key: str | None,
    left_tvg_id: str | None,
    right_tvg_id: str | None,
    left_country: str | None,
    right_country: str | None,
    left_language: str | None,
    right_language: str | None,
    left_quality: str | None,
    right_quality: str | None,
    left_url_checksum: str | None,
    right_url_checksum: str | None,
) -> DuplicateEvaluation:
    reasons: list[str] = []
    score = 0.0
    if left_key and right_key and left_key == right_key:
        score += 0.55
        reasons.append("normalized names match")
    if left_tvg_id and right_tvg_id and left_tvg_id == right_tvg_id:
        score += 0.25
        reasons.append("tvg-id matches")
    if left_url_checksum and right_url_checksum and left_url_checksum == right_url_checksum:
        score += 0.2
        reasons.append("stream URL checksum matches")
    country_conflict = bool(left_country and right_country and left_country != right_country)
    language_conflict = bool(left_language and right_language and left_language != right_language)
    strong_identifier = bool(
        (left_tvg_id and right_tvg_id and left_tvg_id == right_tvg_id)
        or (left_url_checksum and right_url_checksum and left_url_checksum == right_url_checksum)
    )
    contextual_match = bool(
        (left_country and right_country and left_country == right_country)
        or (left_language and right_language and left_language == right_language)
        or (left_quality and right_quality and left_quality != right_quality)
    )
    if not country_conflict:
        score += 0.1
        reasons.append("country compatible")
    if not language_conflict:
        score += 0.1
        reasons.append("language compatible")
    if left_quality != right_quality:
        score += 0.1
        reasons.append("quality differs only by provider label")

    conflict_without_strong_id = (country_conflict or language_conflict) and not strong_identifier
    if conflict_without_strong_id:
        score = min(score, 0.65)
        reasons.append("country or language conflict requires manual review")

    safe_to_cluster = score >= 0.75 and not conflict_without_strong_id and (
        strong_identifier or contextual_match
    )
    return DuplicateEvaluation(confidence=round(min(score, 1.0), 3), reasons=tuple(reasons), safe_to_cluster=safe_to_cluster)


def normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFKC", value)


def normalize_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(character for character in decomposed if not unicodedata.combining(character))
    compact = TOKEN_SPLIT_PATTERN.sub(" ", ascii_text.lower()).strip()
    tokens = [token for token in compact.split() if token not in {"the", "channel", "tv"}]
    return " ".join(tokens)


def strip_provider_prefix(name: str) -> str:
    current = name
    for _iteration in range(3):
        match = PROVIDER_PREFIX_PATTERN.match(current)
        if match is None:
            break
        prefix = (match.group("bracket") or match.group("prefix") or "").lower()
        if any(prefix in aliases for aliases in COUNTRY_ALIASES.values()):
            current = current[match.end() :].strip()
            continue
        break
    return current


def cleanup_display_name(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.replace("_", " ")).strip(" -|:/•\t")
    normalized = re.sub(r"\s+([,.)\]])", r"\1", normalized)
    normalized = re.sub(r"([\[(])\s+", r"\1", normalized)
    return normalized.strip()


def infer_country(*, name: str, group: str | None) -> str | None:
    candidates = [name, group or ""]
    for value in candidates:
        normalized = normalize_key(value)
        first_token = normalized.split(" ", 1)[0] if normalized else ""
        for country, aliases in COUNTRY_ALIASES.items():
            if first_token in aliases or normalized in aliases:
                return country
            if any(f" {alias} " in f" {normalized} " for alias in aliases if len(alias) > 2):
                return country
    return None


def infer_language(*, name: str, group: str | None) -> str | None:
    normalized = f" {normalize_key(name)} {normalize_key(group or '')} "
    for language, aliases in LANGUAGE_ALIASES.items():
        if any(f" {alias} " in normalized for alias in aliases):
            return language
    country = infer_country(name=name, group=group)
    if country in {"United States", "United Kingdom", "Canada", "Australia"}:
        return "English"
    return None


def infer_quality(haystack: str) -> str | None:
    for label, pattern in QUALITY_PATTERNS:
        if re.search(pattern, haystack, re.IGNORECASE):
            return label
    return None


def infer_flags(haystack: str, quality: str | None) -> tuple[str, ...]:
    normalized = f" {normalize_key(haystack)} "
    flags: set[str] = set()
    if any(marker in normalized for marker in (" adult ", " xxx ", " porn ", " 18 ")):
        flags.add("adult")
    if any(marker in normalized for marker in (" shopping ", " qvc ", " hsn ", " shop ")):
        flags.add("shopping")
    if any(marker in normalized for marker in (" religious ", " faith ", " church ", " gospel ")):
        flags.add("religious")
    if any(marker in normalized for marker in (" test ", " backup ", " back up ", " raw feed ", " alt ")):
        flags.add("test_backup")
    if " 24 7 " in normalized or " 24x7 " in normalized:
        flags.add("loop_24_7")
    if quality == "SD":
        flags.add("low_quality")
    return tuple(sorted(flags))


def infer_group(*, name: str, original_group: str | None, haystack: str) -> str:
    group_key = normalize_key(original_group or "")
    candidate_text = f" {normalize_key(original_group or '')} {normalize_key(name)} {normalize_key(haystack)} "
    for group_name, markers in GROUP_PATTERNS:
        if any(f" {normalize_key(marker)} " in candidate_text for marker in markers):
            return group_name
    if original_group and group_key not in GENERIC_GROUPS:
        return "International" if infer_language(name=name, group=original_group) not in {None, "English"} else "Other"
    return "Other"


def infer_content_type(
    *,
    source_content_type: str | None,
    name: str,
    group: str | None,
    stream_url: str,
    haystack: str,
) -> ContentType:
    normalized = f" {normalize_key(haystack)} "
    url_lower = stream_url.lower()
    if source_content_type == "movie":
        return "movie"
    if source_content_type == "series":
        return "series"
    if re.search(r"\bs\d{1,2}\s*e\d{1,3}\b", normalized) or "/series/" in url_lower:
        return "series"
    if any(marker in url_lower for marker in ("/movie/", "/movies/", "/vod/")):
        return "movie"
    if any(marker in normalized for marker in (" movie ", " movies ", " vod ")):
        return "movie"
    if any(marker in url_lower for marker in ("/live/", "/channel/", "/channels/", ".m3u8")):
        return "live_tv"
    if group and infer_group(name=name, original_group=group, haystack=haystack) not in {"Movies", "Other"}:
        return "live_tv"
    if source_content_type == "live_tv":
        return "live_tv"
    return "unknown"
