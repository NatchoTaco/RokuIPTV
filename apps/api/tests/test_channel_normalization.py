from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from streamforge_api.domain.channel_normalization import (
    duplicate_confidence,
    evaluate_filter,
    normalize_channel,
)
from streamforge_api.models import ChannelSourceCandidate, CuratedChannel, DuplicateCluster, RawChannel, Source
from streamforge_api.services.channels import ChannelService


def bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "email": "admin@example.com",
            "password": "correct horse battery",
            "display_name": "Admin",
        },
    )
    assert response.status_code == 201


def make_source(db_session: Session, name: str = "Synthetic Provider") -> Source:
    source = Source(
        name=name,
        source_type="m3u_upload",
        status="healthy",
        config_json={"display_location": "synthetic.m3u"},
        is_enabled=True,
    )
    db_session.add(source)
    db_session.flush()
    return source


def add_raw_channel(
    db_session: Session,
    source: Source,
    *,
    name: str,
    url: str,
    group: str | None = None,
    tvg_id: str | None = None,
    content_type: str = "unknown",
) -> RawChannel:
    channel = RawChannel(
        source_id=source.id,
        original_name=name,
        original_group=group,
        original_url=url,
        original_tvg_id=tvg_id,
        original_tvg_name=None,
        original_logo_url=None,
        source_metadata_json={"content_type": content_type},
        raw_attributes_json={"tvg-id": tvg_id or "", "group-title": group or ""},
        url_checksum=f"checksum-{url.rsplit('/', 1)[-1]}",
        content_type=content_type,
    )
    db_session.add(channel)
    db_session.flush()
    return channel


def test_normalization_handles_prefixes_quality_unicode_and_missing_group() -> None:
    result = normalize_channel(
        original_name="US: Café News HD 60FPS Backup",
        original_group=None,
        source_content_type="unknown",
        stream_url="https://example.com/live/provider/1001.m3u8",
        attributes={"tvg-id": "cafe.news"},
    )

    assert result.display_name == "Café News"
    assert result.normalized_key == "cafe news"
    assert result.country == "United States"
    assert result.language == "English"
    assert result.group_name == "News"
    assert result.quality == "HD"
    assert result.content_type == "live_tv"
    assert "test_backup" in result.flags
    assert any(item["field"] == "group" for item in result.explanations)


def test_normalization_classifies_live_movie_series_and_unknown() -> None:
    live = normalize_channel(
        original_name="Mystery Local",
        original_group="Unknown",
        source_content_type="unknown",
        stream_url="https://example.com/live/user/pass/1.m3u8",
        attributes={},
    )
    movie = normalize_channel(
        original_name="Synthetic Movie",
        original_group="Movies",
        source_content_type="movie",
        stream_url="https://example.com/movie/user/pass/1.mp4",
        attributes={},
    )
    series = normalize_channel(
        original_name="Synthetic Show S01E02",
        original_group="Series",
        source_content_type="series",
        stream_url="https://example.com/series/user/pass/1.mp4",
        attributes={},
    )
    unknown = normalize_channel(
        original_name="Provider Feed",
        original_group=None,
        source_content_type="unknown",
        stream_url="https://example.com/content/1.ts",
        attributes={},
    )

    assert live.content_type == "live_tv"
    assert movie.content_type == "movie"
    assert series.content_type == "series"
    assert unknown.content_type == "unknown"


def test_duplicate_scoring_avoids_same_name_different_country_false_merge() -> None:
    evaluation = duplicate_confidence(
        left_key="abc news",
        right_key="abc news",
        left_tvg_id=None,
        right_tvg_id=None,
        left_country="United States",
        right_country="Australia",
        left_language="English",
        right_language="English",
        left_quality="HD",
        right_quality="HD",
        left_url_checksum="one",
        right_url_checksum="two",
    )

    assert evaluation.confidence <= 0.65
    assert evaluation.safe_to_cluster is False


def test_duplicate_scoring_does_not_merge_identical_names_without_supporting_metadata() -> None:
    evaluation = duplicate_confidence(
        left_key="channel one",
        right_key="channel one",
        left_tvg_id=None,
        right_tvg_id=None,
        left_country=None,
        right_country=None,
        left_language=None,
        right_language=None,
        left_quality="HD",
        right_quality="HD",
        left_url_checksum="one",
        right_url_checksum="two",
    )

    assert evaluation.safe_to_cluster is False


def test_allowlist_precedence_over_aggressive_filtering() -> None:
    result = normalize_channel(
        original_name="US: Test Backup SD",
        original_group=None,
        source_content_type="live_tv",
        stream_url="https://example.com/live/test.m3u8",
        attributes={},
    )

    filtering = evaluate_filter(result, profile="aggressive", manual_visibility_status="always_visible")

    assert filtering.visibility_status == "always_visible"
    assert filtering.action == "allow"
    assert "allowlist override" in filtering.reasons


def test_service_normalizes_duplicates_and_curated_lineup_idempotently(
    db_session: Session,
    client,
) -> None:
    source = make_source(db_session)
    add_raw_channel(
        db_session,
        source,
        name="US: Demo News HD",
        group=None,
        tvg_id="demo.news",
        url="https://example.com/live/demo/news-hd.m3u8",
    )
    add_raw_channel(
        db_session,
        source,
        name="US: Demo News SD",
        group=None,
        tvg_id="demo.news",
        url="https://example.com/live/demo/news-sd.m3u8",
    )
    add_raw_channel(
        db_session,
        source,
        name="UK: Demo News HD",
        group=None,
        tvg_id=None,
        url="https://example.com/live/demo/uk-news.m3u8",
    )
    db_session.commit()

    service = ChannelService(db_session, client.app.state.settings)
    first_job = service.create_normalization_job(source_id=source.id, profile="recommended", process_now=True)
    second_job = service.create_normalization_job(source_id=source.id, profile="recommended", process_now=True)

    clusters = db_session.scalar(select(func.count()).select_from(DuplicateCluster))
    curated = db_session.scalar(select(func.count()).select_from(CuratedChannel))
    candidates = db_session.scalar(select(func.count()).select_from(ChannelSourceCandidate))
    us_channel = db_session.scalar(select(RawChannel).where(RawChannel.original_name == "US: Demo News HD"))
    uk_channel = db_session.scalar(select(RawChannel).where(RawChannel.original_name == "UK: Demo News HD"))

    assert first_job.status == "succeeded"
    assert second_job.status == "succeeded"
    assert clusters == 1
    assert curated == 2
    assert candidates == 3
    assert us_channel is not None
    assert us_channel.normalized_name == "Demo News"
    assert us_channel.normalized_group == "News"
    assert uk_channel is not None
    assert uk_channel.duplicate_cluster_id is None


def test_service_processes_large_generated_dataset_in_batches(
    db_session: Session,
    client,
) -> None:
    client.app.state.settings.channel_normalization_batch_size = 200
    source = make_source(db_session, "Large Synthetic Provider")
    for index in range(1200):
        add_raw_channel(
            db_session,
            source,
            name=f"US: Large News {index} HD",
            group=None,
            tvg_id=f"large.news.{index}",
            url=f"https://example.com/live/large/{index}.m3u8",
            content_type="unknown",
        )
    db_session.commit()

    service = ChannelService(db_session, client.app.state.settings)
    job = service.create_normalization_job(source_id=source.id, profile="recommended", process_now=True)
    normalized = db_session.scalar(
        select(func.count()).select_from(RawChannel).where(RawChannel.normalized_at.is_not(None))
    )

    assert job.status == "succeeded"
    assert job.total_raw_channels == 1200
    assert normalized == 1200
    assert job.stats["normalized_channels"] == 1200


def test_channel_api_normalizes_and_never_returns_stream_credentials(
    client: TestClient,
    db_session: Session,
) -> None:
    bootstrap_admin(client)
    source = make_source(db_session, "Credential Provider")
    add_raw_channel(
        db_session,
        source,
        name="US: Secure News HD",
        group=None,
        tvg_id="secure.news",
        url="https://example.com/live/provider-user/provider-pass/1.m3u8?token=provider-token",
        content_type="unknown",
    )
    db_session.commit()

    job_response = client.post(
        "/api/v1/channels/normalization-jobs",
        json={"source_id": source.id, "profile": "recommended", "process_now": True},
    )
    list_response = client.get("/api/v1/channels")
    queue_response = client.get("/api/v1/cleanup/queues")

    assert job_response.status_code == 202
    assert job_response.json()["status"] == "succeeded"
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["normalized_name"] == "Secure News"
    assert queue_response.status_code == 200
    combined = f"{job_response.text} {list_response.text} {queue_response.text}"
    assert "provider-user" not in combined
    assert "provider-pass" not in combined
    assert "provider-token" not in combined
