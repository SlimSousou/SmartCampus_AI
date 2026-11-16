from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.models import AuditEvent, Role, User


def create_test_client() -> TestClient:
    app = create_app("sqlite://", auto_create_tables=True)
    return TestClient(app)


def register(client: TestClient, email: str = "candidate@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test Candidate", "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, email: str = "candidate@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert response.status_code == 200
    return response.json()


def test_registration_never_accepts_a_client_selected_role() -> None:
    with create_test_client() as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "candidate@example.com",
                "full_name": "Test Candidate",
                "password": "correct-horse-battery",
                "role": "admin",
            },
        )
        assert response.status_code == 422

        created = register(client)
        assert created["role"] == Role.CANDIDATE.value
        assert "password_hash" not in created


def test_login_current_user_and_generic_invalid_credentials() -> None:
    with create_test_client() as client:
        register(client)
        tokens = login(client)
        response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert response.status_code == 200
        assert response.json()["email"] == "candidate@example.com"

        invalid = client.post(
            "/api/v1/auth/login",
            json={"email": "candidate@example.com", "password": "wrong-password"},
        )
        assert invalid.status_code == 401
        assert invalid.headers["content-type"].startswith("application/problem+json")


def test_refresh_rotates_cookie_and_rejects_replay_without_csrf() -> None:
    with create_test_client() as client:
        register(client)
        login(client)
        previous_refresh = client.cookies.get("sc_refresh")
        previous_csrf = client.cookies.get("sc_csrf")

        missing_csrf = client.post("/api/v1/auth/refresh")
        assert missing_csrf.status_code == 401

        refreshed = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": previous_csrf})
        assert refreshed.status_code == 200
        assert client.cookies.get("sc_refresh") != previous_refresh
        rotated_refresh = client.cookies.get("sc_refresh")
        rotated_csrf = client.cookies.get("sc_csrf")

        client.cookies.set("sc_refresh", previous_refresh, path="/api/v1/auth")
        client.cookies.set("sc_csrf", previous_csrf, path="/api/v1/auth")
        replay = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": previous_csrf})
        assert replay.status_code == 401

        client.cookies.set("sc_refresh", rotated_refresh, path="/api/v1/auth")
        client.cookies.set("sc_csrf", rotated_csrf, path="/api/v1/auth")
        revoked_family = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": rotated_csrf})
        assert revoked_family.status_code == 401


def test_admin_role_changes_are_forbidden_to_candidates_and_audited() -> None:
    with create_test_client() as client:
        candidate = register(client)
        candidate_token = login(client)["access_token"]
        denied = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {candidate_token}"})
        assert denied.status_code == 403

        session_factory = client.app.state.session_factory
        db = session_factory()
        try:
            user = db.scalar(select(User).where(User.email == "candidate@example.com"))
            user.role = Role.ADMIN.value
            db.commit()
        finally:
            db.close()

        admin_token = login(client)["access_token"]
        new_candidate = register(client, "another@example.com")
        changed = client.patch(
            f"/api/v1/admin/users/{new_candidate['id']}/roles",
            json={"role": Role.ACADEMIC_ISB.value},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert changed.status_code == 200
        assert changed.json()["role"] == Role.ACADEMIC_ISB.value

        db = client.app.state.session_factory()
        try:
            event = db.scalar(select(AuditEvent).where(AuditEvent.subject_user_id == UUID(new_candidate["id"])))
            assert event is not None
            assert event.action == "user.role_changed"
        finally:
            db.close()


def test_last_active_admin_cannot_remove_own_admin_role() -> None:
    with create_test_client() as client:
        candidate = register(client)
        tokens = login(client)
        session_factory = client.app.state.session_factory
        db = session_factory()
        try:
            user = db.scalar(select(User).where(User.id == UUID(candidate["id"])))
            user.role = Role.ADMIN.value
            db.commit()
        finally:
            db.close()

        response = client.patch(
            f"/api/v1/admin/users/{candidate['id']}/roles",
            json={"role": Role.CANDIDATE.value},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 409