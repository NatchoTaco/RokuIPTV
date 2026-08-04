from fastapi.testclient import TestClient


def bootstrap_admin(client: TestClient, password: str = "correct horse battery") -> None:
    response = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "email": "admin@example.com",
            "password": password,
            "display_name": "Admin",
        },
    )
    assert response.status_code == 201


def test_admin_can_be_created_once(client: TestClient) -> None:
    bootstrap_admin(client)

    response = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "email": "second@example.com",
            "password": "correct horse battery",
            "display_name": "Second",
        },
    )

    assert response.status_code == 409


def test_admin_can_sign_in_and_sign_out(client: TestClient) -> None:
    bootstrap_admin(client)
    sign_out_response = client.post("/api/v1/auth/sign-out")
    assert sign_out_response.status_code == 200

    unauthorized_response = client.get("/api/v1/auth/me")
    assert unauthorized_response.status_code == 401

    sign_in_response = client.post(
        "/api/v1/auth/sign-in",
        json={"email": "admin@example.com", "password": "correct horse battery"},
    )
    assert sign_in_response.status_code == 200
    assert sign_in_response.json()["user"]["email"] == "admin@example.com"

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["is_admin"] is True
