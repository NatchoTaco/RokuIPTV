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


def test_channel_protect_unprotect_round_trip_preserves_visibility_and_preview(
    client: TestClient,
    db_session: Session,
) -> None:
    bootstrap_admin(client)
    source = make_source(db_session, "Manual Protection Provider")
    channel = add_raw_channel(
        db_session,
        source,
        name="US: Test Backup SD",
        group=None,
        tvg_id="manual.protection",
        url="https://example.com/live/provider/channel.m3u8",
        content_type="live_tv",
    )
    db_session.commit()

    protected_response = client.patch(
        f"/api/v1/channels/{channel.id}",
        json={"visibility_status": "always_visible", "protected_from_auto_merge": True},
    )
    protected_filter_response = client.get("/api/v1/channels?visibility_status=protected")
    protected_preview_response = client.post("/api/v1/cleanup/preview", json={"profile": "aggressive"})

    assert protected_response.status_code == 200
    assert protected_response.json()["protected_from_auto_merge"] is True
    assert protected_response.json()["visibility_status"] == "always_visible"
    assert protected_filter_response.status_code == 200
    assert [item["id"] for item in protected_filter_response.json()["items"]] == [channel.id]
    assert protected_preview_response.status_code == 200
    assert protected_preview_response.json()["protected_count"] == 1

    unprotected_response = client.patch(
        f"/api/v1/channels/{channel.id}",
        json={"protected_from_auto_merge": False},
    )
    unprotected_filter_response = client.get("/api/v1/channels?visibility_status=protected")
    unprotected_preview_response = client.post("/api/v1/cleanup/preview", json={"profile": "aggressive"})
    db_session.expire_all()
    persisted_channel = db_session.get(RawChannel, channel.id)

    assert unprotected_response.status_code == 200
    assert unprotected_response.json()["protected_from_auto_merge"] is False
    assert unprotected_response.json()["visibility_status"] == "always_visible"
    assert unprotected_filter_response.status_code == 200
    assert unprotected_filter_response.json()["items"] == []
    assert unprotected_preview_response.status_code == 200
    assert unprotected_preview_response.json()["protected_count"] == 0
    assert persisted_channel is not None
    assert persisted_channel.protected_from_auto_merge is False
    assert persisted_channel.manual_visibility_status == "always_visible"
    assert persisted_channel.visibility_status == "always_visible"


def test_duplicate_cluster_protect_unprotect_preserves_membership_and_visibility(
    client: TestClient,
    db_session: Session,
) -> None:
    bootstrap_admin(client)
    source = make_source(db_session, "Duplicate Protection Provider")
    add_raw_channel(
        db_session,
        source,
        name="US: Demo News HD",
        group=None,
        tvg_id="duplicate.protection",
        url="https://example.com/live/demo/news-hd.m3u8",
        content_type="live_tv",
    )
    hidden_channel = add_raw_channel(
        db_session,
        source,
        name="US: Demo News SD",
        group=None,
        tvg_id="duplicate.protection",
        url="https://example.com/live/demo/news-sd.m3u8",
        content_type="live_tv",
    )
    db_session.commit()

    job_response = client.post(
        "/api/v1/channels/normalization-jobs",
        json={"source_id": source.id, "profile": "recommended", "process_now": True},
    )
    db_session.expire_all()
    cluster = db_session.scalar(select(DuplicateCluster))

    assert job_response.status_code == 202
    assert cluster is not None

    persisted_hidden_channel = db_session.get(RawChannel, hidden_channel.id)
    assert persisted_hidden_channel is not None
    persisted_hidden_channel.manual_visibility_status = "hidden"
    persisted_hidden_channel.visibility_status = "hidden"
    db_session.commit()

    protected_response = client.post(f"/api/v1/cleanup/duplicates/{cluster.id}/protect")
    db_session.expire_all()
    protected_channels = db_session.scalars(
        select(RawChannel).where(RawChannel.duplicate_cluster_id == cluster.id)
    ).all()

    assert protected_response.status_code == 200
    assert protected_response.json()["cluster"]["review_status"] == "protected"
    assert len(protected_channels) == 2
    assert all(channel.protected_from_auto_merge for channel in protected_channels)

    unprotected_response = client.post(f"/api/v1/cleanup/duplicates/{cluster.id}/unprotect")
    db_session.expire_all()
    unprotected_cluster = db_session.get(DuplicateCluster, cluster.id)
    unprotected_channels = db_session.scalars(
        select(RawChannel).where(RawChannel.duplicate_cluster_id == cluster.id)
    ).all()
    persisted_hidden_channel = db_session.get(RawChannel, hidden_channel.id)

    assert unprotected_response.status_code == 200
    assert unprotected_response.json()["cluster"]["review_status"] == "pending_review"
    assert unprotected_cluster is not None
    assert unprotected_cluster.review_status == "pending_review"
    assert len(unprotected_channels) == 2
    assert all(not channel.protected_from_auto_merge for channel in unprotected_channels)
    assert persisted_hidden_channel is not None
    assert persisted_hidden_channel.manual_visibility_status == "hidden"
    assert persisted_hidden_channel.visibility_status == "hidden"


def test_clear_all_manual_protections_preserves_allow_and_hide_decisions(
    client: TestClient,
    db_session: Session,
) -> None:
    bootstrap_admin(client)
    source = make_source(db_session, "Clear Protections Provider")
    allowed_channel = add_raw_channel(
        db_session,
        source,
        name="US: Allowed News HD",
        url="https://example.com/live/demo/allowed.m3u8",
        content_type="live_tv",
    )
    hidden_channel = add_raw_channel(
        db_session,
        source,
        name="US: Hidden News HD",
        url="https://example.com/live/demo/hidden.m3u8",
        content_type="live_tv",
    )
    allowed_channel.manual_visibility_status = "always_visible"
    allowed_channel.visibility_status = "always_visible"
    allowed_channel.protected_from_auto_merge = True
    hidden_channel.manual_visibility_status = "hidden"
    hidden_channel.visibility_status = "hidden"
    hidden_channel.protected_from_auto_merge = True
    db_session.commit()

    summary_response = client.get("/api/v1/cleanup/protections")
    clear_response = client.post("/api/v1/cleanup/protections/clear")
    preview_response = client.post("/api/v1/cleanup/preview", json={"profile": "aggressive"})
    db_session.expire_all()
    persisted_allowed_channel = db_session.get(RawChannel, allowed_channel.id)
    persisted_hidden_channel = db_session.get(RawChannel, hidden_channel.id)

    assert summary_response.status_code == 200
    assert summary_response.json()["protected_channel_count"] == 2
    assert summary_response.json()["total_protection_count"] == 2
    assert clear_response.status_code == 200
    assert clear_response.json()["total_protection_count"] == 0
    assert "2 manual protection override" in clear_response.json()["message"]
    assert preview_response.status_code == 200
    assert preview_response.json()["protected_count"] == 0
    assert persisted_allowed_channel is not None
    assert persisted_allowed_channel.protected_from_auto_merge is False
    assert persisted_allowed_channel.manual_visibility_status == "always_visible"
    assert persisted_allowed_channel.visibility_status == "always_visible"
    assert persisted_hidden_channel is not None
    assert persisted_hidden_channel.protected_from_auto_merge is False
    assert persisted_hidden_channel.manual_visibility_status == "hidden"
    assert persisted_hidden_channel.visibility_status == "hidden"
