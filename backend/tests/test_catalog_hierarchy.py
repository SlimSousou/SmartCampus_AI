from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.models import Role, User


PASSWORD = "correct-horse-battery"


def register(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test User", "password": PASSWORD},
    )
    assert response.status_code == 201, response.text


def token_for_role(client: TestClient, email: str, role: Role) -> str:
    db = client.app.state.session_factory()
    try:
        user = db.scalar(select(User).where(User.email == email))
        user.role = role.value
        db.commit()
    finally:
        db.close()
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_specialty_curriculum_and_subject_api_relationships_and_scopes() -> None:
    with TestClient(create_app("sqlite://", auto_create_tables=True)) as client:
        register(client, "iit@example.com")
        iit_token = token_for_role(client, "iit@example.com", Role.ACADEMIC_IIT)
        register(client, "isb@example.com")
        isb_token = token_for_role(client, "isb@example.com", Role.ACADEMIC_ISB)

        program_response = client.post(
            "/api/v1/programs",
            headers=headers(iit_token),
            json={"institution": "IIT", "level": "licence", "name": "Licence Informatique"},
        )
        assert program_response.status_code == 201, program_response.text
        program = program_response.json()
        client.post(f"/api/v1/programs/{program['id']}/publish", headers=headers(iit_token))

        specialty_response = client.post(
            "/api/v1/specialties",
            headers=headers(iit_token),
            json={"program_id": program["id"], "name": "Génie logiciel"},
        )
        assert specialty_response.status_code == 201, specialty_response.text
        specialty = specialty_response.json()

        curriculum_response = client.post(
            "/api/v1/curricula",
            headers=headers(iit_token),
            json={
                "program_id": program["id"],
                "specialty_id": specialty["id"],
                "name": "Programme 2026-2027",
                "academic_year": "2026-2027",
            },
        )
        assert curriculum_response.status_code == 201, curriculum_response.text
        curriculum = curriculum_response.json()

        subject_response = client.post(
            "/api/v1/subjects",
            headers=headers(iit_token),
            json={
                "curriculum_id": curriculum["id"],
                "code": "INF101",
                "name": "Algorithmique",
                "semester": 1,
                "credits": "3.00",
                "coefficient": "2.00",
                "hours": "45.00",
            },
        )
        assert subject_response.status_code == 201, subject_response.text
        subject = subject_response.json()

        duplicate = client.post(
            "/api/v1/subjects",
            headers=headers(iit_token),
            json={"curriculum_id": curriculum["id"], "code": "inf101", "name": "Doublon"},
        )
        assert duplicate.status_code == 409

        assert client.get("/api/v1/specialties", params={"program_id": program["id"]}).json()[0]["id"] == specialty["id"]
        assert client.get("/api/v1/curricula", params={"program_id": program["id"]}).json()[0]["id"] == curriculum["id"]
        assert client.get("/api/v1/subjects", params={"program_id": program["id"], "semester": 1}).json()[0]["id"] == subject["id"]

        wrong_institution = client.patch(
            f"/api/v1/subjects/{subject['id']}",
            headers=headers(isb_token),
            json={"name": "Modification ISB"},
        )
        assert wrong_institution.status_code == 403

        null_curriculum = client.patch(
            f"/api/v1/subjects/{subject['id']}",
            headers=headers(iit_token),
            json={"curriculum_id": None},
        )
        assert null_curriculum.status_code == 422

        other_program = client.post(
            "/api/v1/programs",
            headers=headers(iit_token),
            json={"institution": "IIT", "level": "prepa", "name": "Préparatoire"},
        ).json()
        wrong_specialty = client.post(
            "/api/v1/curricula",
            headers=headers(iit_token),
            json={"program_id": other_program["id"], "specialty_id": specialty["id"], "name": "Incohérent"},
        )
        assert wrong_specialty.status_code == 422
