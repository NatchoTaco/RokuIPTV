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
