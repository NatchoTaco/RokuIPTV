from fastapi.testclient import TestClient


def test_health_reports_live_dependencies(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "ok"
    assert body["setup_complete"] is False


def test_setup_state_persists_installation_mode(client: TestClient) -> None:
    admin_response = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "email": "admin@example.com",
            "password": "correct horse battery",
            "display_name": "Admin",
        },
    )
    assert admin_response.status_code == 201

    update_response = client.patch(
        "/api/v1/setup/state",
        json={"installation_mode": "local_only"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_complete"] is True

    state_response = client.get("/api/v1/setup/state")
    assert state_response.status_code == 200
    body = state_response.json()
    assert body["installation_mode"] == "local_only"
    assert body["completed_steps"] == ["account", "installation_mode"]
