from streamforge_api.domain.m3u import M3uParser
from streamforge_api.domain.url_safety import SafeUrlValidator


def test_m3u_parser_handles_bom_comments_attrs_duplicates_and_unicode() -> None:
    playlist = """\ufeff#EXTM3U
# comment

#EXTINF:-1 tvg-id="demo.news" tvg-name="Demo News" tvg-logo="https://example.com/logo.png" group-title="News",Demo News
https://example.com/live/news/master.m3u8
#EXTINF:-1 tvg-id='demo.cafe' group-title='Culture',Café International
https://example.com/live/cafe/master.m3u8
#EXTINF:-1 tvg-id="demo.dup" group-title="News",Duplicate URL
https://example.com/live/news/master.m3u8
#EXTINF:-1 group-title="Broken",Bad Local URL
file:///etc/passwd
#EXTINF:-1 group-title="Broken",Missing URL
""".encode("utf-8")

    result = M3uParser().parse_bytes(playlist)

    assert len(result.channels) == 3
    assert result.group_count == 2
    assert result.channels[0].original_name == "Demo News"
    assert result.channels[0].original_tvg_id == "demo.news"
    assert result.channels[0].original_tvg_name == "Demo News"
    assert result.channels[0].original_logo_url == "https://example.com/logo.png"
    assert result.channels[1].original_name == "Café International"
    assert result.channels[2].original_url == result.channels[0].original_url
    assert any("Only HTTP and HTTPS" in failure for failure in result.failures)
    assert any("missing a stream URL" in failure for failure in result.failures)


def test_safe_url_validator_rejects_unsupported_and_private_sources() -> None:
    validator = SafeUrlValidator(allow_private_destinations=False)

    assert not validator.validate_source_url("file:///tmp/playlist.m3u").is_safe
    assert not validator.validate_source_url("ftp://example.com/playlist.m3u").is_safe
    private_result = validator.validate_source_url("http://127.0.0.1/playlist.m3u")

    assert not private_result.is_safe
    assert "private" in private_result.errors[0] or "Localhost" in private_result.errors[0]


def test_m3u_parser_handles_provider_style_extinf_groups_and_commas() -> None:
    playlist = """#EXTM3U
#EXTINF:-1 tvg-name="News, Local" tvg-id="news.local" group-title="US, News" tvg-logo="https://example.com/logo,1.png",News, Local
https://example.com/live/user/pass/1001.m3u8
#EXTINF:-1 group-title = 'Movies, Featured' tvg-id='movie.one' tvg-name='Movie One',Movie One
https://example.com/movie/user/pass/2001.mp4
#EXTINF:-1 tvg-id=series.one group_title=Series tvg-name="Show S01E02",Show S01E02
https://example.com/series/user/pass/3001.mp4
#EXTINF:-1 GROUP-TITLE="International Cafe" tvg-id="unknown.one",Mystery Stream
https://example.com/content/4001.ts
"""

    result = M3uParser().parse_text(playlist, include_content_types={"live_tv"})

    assert result.total_entry_count == 4
    assert result.group_count == 4
    assert result.content_counts.live_tv == 1
    assert result.content_counts.movie == 1
    assert result.content_counts.series == 1
    assert result.content_counts.unknown == 1
    assert result.excluded_count == 3
    assert result.channels[0].original_group == "US, News"
    assert result.samples[0].name == "News, Local"


def test_m3u_parser_handles_case_variants_unquoted_values_and_unknown_live_urls() -> None:
    playlist = """#EXTM3U
#EXTINF:-1 TVG-ID=demo.local GROUP-TITLE=Unknown tvg-name='US: Local Mystery HD',US: Local Mystery HD
https://example.com/live/user/pass/4001.m3u8
#EXTINF:-1 tvg-id=demo.provider group="Sports" provider-channel-id=abc-123,Provider Sports
https://example.com/channel/user/pass/4002.ts
"""

    result = M3uParser().parse_text(playlist, include_content_types={"live_tv", "unknown"})

    assert result.total_entry_count == 2
    assert result.content_counts.live_tv == 2
    assert result.channels[0].original_group == "Unknown"
    assert result.channels[0].attributes["tvg-id"] == "demo.local"
    assert result.channels[1].attributes["provider-channel-id"] == "abc-123"


def test_m3u_parser_summarizes_large_synthetic_playlist_without_real_provider_data() -> None:
    lines = ["#EXTM3U"]
    for index in range(1, 1001):
        lines.append(f'#EXTINF:-1 tvg-id="live.{index}" group-title="Group {index % 10}",Live {index}')
        lines.append(f"https://example.com/live/demo/{index}.m3u8")
    playlist = "\n".join(lines)

    result = M3uParser().parse_text(
        playlist,
        include_content_types={"live_tv"},
        keep_channels=False,
    )

    assert result.total_entry_count == 1000
    assert result.selected_entry_count == 1000
    assert len(result.channels) == 0
    assert result.group_count == 10
    assert result.failures == []
