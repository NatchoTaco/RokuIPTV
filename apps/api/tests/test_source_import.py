from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from streamforge_api.models import PlaylistImport, RawChannel, Source
from streamforge_api.services.source_import import SourceImportService


def bootstrap_admin(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "email": "admin@example.com",
            "password": "correct horse battery",
            "display_name": "Admin",
        },
    )
    assert response.status_code == 201
    return response.json()["user"]


def test_demo_source_import_runs_as_async_job_and_preserves_raw_channels(
    client: TestClient,
    db_session: Session,
) -> None:
    bootstrap_admin(client)
    create_response = client.post(
        "/api/v1/sources/demo",
        json={"name": "Demo Source", "refresh_interval_minutes": None},
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["job"]["id"]

    job_response = SourceImportService(
        db_session,
        client.app.state.settings,
    ).process_import_job(job_id)

    assert job_response.status == "succeeded"
    assert job_response.progress_percent == 100
    raw_count = db_session.scalar(select(func.count()).select_from(RawChannel))
    import_count = db_session.scalar(select(func.count()).select_from(PlaylistImport))
    source = db_session.scalar(select(Source).where(Source.name == "Demo Source"))
    first_channel = db_session.scalar(
        select(RawChannel).where(RawChannel.original_name == "Demo News")
    )

    assert raw_count == 3
    assert import_count == 1
    assert source is not None
    assert source.status == "healthy"
    assert first_channel is not None
    assert first_channel.original_url == "https://example.com/streamforge/demo/news/master.m3u8"
    assert first_channel.normalized_name is None


<<<<<<< HEAD
=======
def test_repeat_import_replaces_raw_rows_for_source(
    client: TestClient,
    db_session: Session,
) -> None:
    bootstrap_admin(client)
    create_response = client.post(
        "/api/v1/sources/demo",
        json={"name": "Demo Source", "refresh_interval_minutes": None},
    )
    assert create_response.status_code == 201
    source_id = create_response.json()["source"]["id"]
    first_job_id = create_response.json()["job"]["id"]

    service = SourceImportService(db_session, client.app.state.settings)
    service.process_import_job(first_job_id)
    refresh_response = client.post(f"/api/v1/sources/{source_id}/refresh")
    assert refresh_response.status_code == 202
    service.process_import_job(refresh_response.json()["id"])

    raw_count = db_session.scalar(select(func.count()).select_from(RawChannel))
    import_count = db_session.scalar(select(func.count()).select_from(PlaylistImport))

    assert raw_count == 3
    assert import_count == 2


>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
def test_upload_source_validation_reports_counts(client: TestClient) -> None:
    bootstrap_admin(client)
    playlist = b"""#EXTM3U
#EXTINF:-1 tvg-id="one" group-title="Group One",One
https://example.com/one.m3u8
#EXTINF:-1 tvg-id="two" group-title="Group Two",Two
https://example.com/two.m3u8
"""

    response = client.post(
        "/api/v1/sources/validate-upload",
        files={"file": ("synthetic.m3u", playlist, "audio/mpegurl")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["playlist_reachable"] is True
    assert body["channel_count"] == 2
    assert body["group_count"] == 2
<<<<<<< HEAD
=======


def test_url_source_creation_never_returns_credentials(client: TestClient) -> None:
    bootstrap_admin(client)
    sensitive_url = (
        "http://example.com/get.php?"
        "username=provider-user&password=provider-pass&type=m3u&token=provider-token"
    )

    create_response = client.post(
        "/api/v1/sources/m3u-url",
        json={
            "name": "Sensitive URL",
            "url": sensitive_url,
            "refresh_interval_minutes": None,
            "enabled_content_types": ["live_tv"],
            "confirm_large_import": False,
        },
    )
    list_response = client.get("/api/v1/sources")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    combined_response = f"{create_response.text} {list_response.text}"
    assert "provider-user" not in combined_response
    assert "provider-pass" not in combined_response
    assert "provider-token" not in combined_response
    assert "********" in combined_response


def test_url_validation_errors_never_return_credentials(client: TestClient) -> None:
    bootstrap_admin(client)
    sensitive_url = (
        "https://example.com/get.php?"
        "username=provider-user&password=provider-pass&type=m3u&token=provider-token&"
        f"padding={'x' * 4096}"
    )

    response = client.post(
        "/api/v1/sources/validate-url",
        json={"url": sensitive_url, "enabled_content_types": ["live_tv"]},
    )

    assert response.status_code == 422
    assert "provider-user" not in response.text
    assert "provider-pass" not in response.text
    assert "provider-token" not in response.text
    assert "********" in response.text


def test_large_synthetic_upload_requires_confirmation_warning(client: TestClient) -> None:
    bootstrap_admin(client)
    client.app.state.settings.source_large_playlist_warning_entries = 10
    client.app.state.settings.source_import_confirmation_threshold_entries = 20
    lines = ["#EXTM3U"]
    for index in range(25):
        lines.append(f'#EXTINF:-1 group-title="Group {index % 5}",Live {index}')
        lines.append(f"https://example.com/live/demo/{index}.m3u8")
    playlist = "\n".join(lines).encode("utf-8")

    response = client.post(
        "/api/v1/sources/validate-upload",
        files={"file": ("large-synthetic.m3u", playlist, "audio/mpegurl")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_entry_count"] == 25
    assert body["selected_entry_count"] == 25
    assert body["requires_confirmation"] is True
    assert body["estimated_database_rows"] == 25
    assert any("unusually large" in warning for warning in body["warnings"])


def test_movie_only_validation_is_deferred_and_not_selected(client: TestClient) -> None:
    bootstrap_admin(client)
    playlist = b"""#EXTM3U
#EXTINF:-1 group-title="Movies",Synthetic Movie
https://example.com/movie/demo/1.mp4
"""

    response = client.post(
        "/api/v1/sources/validate-upload",
        data={"enabled_content_types": "movie"},
        files={"file": ("movie-synthetic.m3u", playlist, "audio/mpegurl")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["playlist_reachable"] is True
    assert body["channel_count"] == 0
    assert body["selected_entry_count"] == 0
    assert body["excluded_entry_count"] == 1
    assert body["content_counts"]["movie"] == 1
    assert body["selected_content_types"] == []
    assert body["deferred_content_types"] == ["movie"]
    assert any("storage is deferred" in warning for warning in body["warnings"])
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
