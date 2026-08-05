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
