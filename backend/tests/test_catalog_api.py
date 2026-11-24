from datetime import date, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.models import Program, Role, User


PASSWORD = "correct-horse-battery"


def create_client() -> TestClient:
    return TestClient(create_app("sqlite://", auto_create_tables=True))


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test Academic", "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()


def set_role(client: TestClient, email: str, role: Role) -> str:
    session_factory = client.app.state.session_factory
    db = session_factory()
    try:
        user = db.scalar(select(User).where(User.email == email))
        user.role = role.value
        db.commit()
    finally:
        db.close()
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_program(client: TestClient, token: str, institution: str = "IIT", name: str = "Programme API") -> dict:
    response = client.post(
        "/api/v1/programs",
        headers=auth(token),
        json={
            "institution": institution,
            "level": "engineering",
            "name": name,
            "description": "Programme de test API",
            "duration": "5 ans",
            "admission_requirements": "Baccalaureat requis",
            "career_prospects": "Ingenieur",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_catalog_public_listing_filters_and_hides_drafts() -> None:
    with create_client() as client:
        db = client.app.state.session_factory()
        try:
            published = Program(
                institution="IIT",
                name="Ingenierie publique",
                level="engineering",
                description="Informatique",
                is_published=True,
            )
            draft = Program(
                institution="IIT",
                name="Formation brouillon",
                level="bachelor",
                description="Ne doit pas être publique",
                is_published=False,
            )
            demo = Program(
                institution="ISB",
                name="Programme demo",
                level="other",
                description="Fictif",
                is_published=True,
                is_demo=True,
            )
            db.add_all([published, draft, demo])
            db.commit()
            published_id = str(published.id)
            draft_id = str(draft.id)
        finally:
            db.close()

        response = client.get("/api/v1/programs", params={"institution": "IIT", "q": "info"})
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [published_id]
        assert client.get(f"/api/v1/programs/{draft_id}").status_code == 404


def test_catalog_writes_require_correct_academic_scope() -> None:
    with create_client() as client:
        register(client, "academic@example.com")
        academic_token = set_role(client, "academic@example.com", Role.ACADEMIC_IIT)
        candidate = register(client, "candidate@example.com")
        candidate_token = client.post(
            "/api/v1/auth/login", json={"email": candidate["email"], "password": PASSWORD}
        ).json()["access_token"]

        forbidden = client.post(
            "/api/v1/programs",
            headers=auth(candidate_token),
            json={"institution": "IIT", "level": "engineering", "name": "Candidate write"},
        )
        assert forbidden.status_code == 403

        program = make_program(client, academic_token)
        assert program["is_published"] is False
        outside_scope = client.post(
            "/api/v1/programs",
            headers=auth(academic_token),
            json={"institution": "ISB", "level": "other", "name": "Wrong institution"},
        )
        assert outside_scope.status_code == 403

        moved = client.patch(
            f"/api/v1/programs/{program['id']}",
            headers=auth(academic_token),
            json={"institution": "ISB"},
        )
        assert moved.status_code == 403

        published = client.post(f"/api/v1/programs/{program['id']}/publish", headers=auth(academic_token))
        assert published.status_code == 200
        assert published.json()["is_published"] is True


def test_fee_and_admission_publication_validity_and_republication() -> None:
    with create_client() as client:
        register(client, "iit@example.com")
        token = set_role(client, "iit@example.com", Role.ACADEMIC_IIT)
        program = make_program(client, token, name="Catalogue officiel")
        client.post(f"/api/v1/programs/{program['id']}/publish", headers=auth(token))

        fee_response = client.post(
            "/api/v1/fees",
            headers=auth(token),
            json={
                "program_id": program["id"],
                "label": "Frais annuels",
                "amount": "6500.000",
                "currency": "TND",
                "period": "annual",
                "valid_from": str(date.today() - timedelta(days=1)),
            },
        )
        assert fee_response.status_code == 201, fee_response.text
        fee = fee_response.json()
        assert fee["status"] == "draft"
        assert fee["published_at"] is None
        assert client.get("/api/v1/fees", params={"program_id": program["id"]}).json() == []

        condition_response = client.post(
            "/api/v1/admission-conditions",
            headers=auth(token),
            json={
                "program_id": program["id"],
                "kind": "diploma",
                "title": "Baccalaureat",
                "description": "Diplome requis",
                "required": True,
                "threshold": "10.000",
            },
        )
        assert condition_response.status_code == 201, condition_response.text
        condition = condition_response.json()

        term_response = client.post(
            "/api/v1/payment-terms",
            headers=auth(token),
            json={
                "program_id": program["id"],
                "fee_id": fee["id"],
                "method": "bank_transfer",
                "title": "Paiement en trois tranches",
                "installments": 3,
                "down_payment_percent": "30.00",
            },
        )
        assert term_response.status_code == 201, term_response.text
        term = term_response.json()
        assert term["status"] == "draft"

        assert client.post(f"/api/v1/fees/{fee['id']}/publish", headers=auth(token)).status_code == 200
        assert client.post(
            f"/api/v1/admission-conditions/{condition['id']}/publish", headers=auth(token)
        ).status_code == 200
        assert client.post(f"/api/v1/payment-terms/{term['id']}/publish", headers=auth(token)).status_code == 200
        public_info = client.get(f"/api/v1/programs/{program['id']}/official-info")
        assert public_info.status_code == 200
        assert public_info.json()["complete"] == {"fees": True, "payment_terms": True, "admission_conditions": True}
        assert len(public_info.json()["fees"]) == 1
        assert len(public_info.json()["payment_terms"]) == 1
        assert len(public_info.json()["admission_conditions"]) == 1

        changed = client.patch(
            f"/api/v1/fees/{fee['id']}",
            headers=auth(token),
            json={"amount": "7000.000"},
        )
        assert changed.status_code == 200
        assert changed.json()["status"] == "draft"
        assert client.get("/api/v1/fees", params={"program_id": program["id"]}).json() == []


def test_catalog_input_validation_and_wrong_role() -> None:
    with create_client() as client:
        register(client, "isb@example.com")
        token = set_role(client, "isb@example.com", Role.ACADEMIC_ISB)
        program = make_program(client, token, institution="ISB", name="Programme ISB")

        invalid_fee = client.post(
            "/api/v1/fees",
            headers=auth(token),
            json={"program_id": program["id"], "label": "Invalid", "amount": -1, "currency": "dinar", "period": "monthly"},
        )
        assert invalid_fee.status_code == 422

        invalid_condition_period = client.post(
            "/api/v1/admission-conditions",
            headers=auth(token),
            json={
                "program_id": program["id"],
                "kind": "diploma",
                "title": "Invalid period",
                "valid_from": "2027-01-02",
                "valid_until": "2027-01-01",
            },
        )
        assert invalid_condition_period.status_code == 422

        archived = client.post(f"/api/v1/programs/{program['id']}/unpublish", headers=auth(token))
        assert archived.status_code == 200
        assert client.get(f"/api/v1/programs/{program['id']}").status_code == 404


def test_program_filtering_by_level_and_pagination() -> None:
    with create_client() as client:
        register(client, "iit-filter@example.com")
        token = set_role(client, "iit-filter@example.com", Role.ACADEMIC_IIT)
        first = make_program(client, token, name="Licence informatique")
        second = make_program(client, token, name="Ingenierie reseau")
        legacy_level = client.post(
            "/api/v1/programs",
            headers=auth(token),
            json={"institution": "IIT", "level": "licence", "name": "Licence format ancien"},
        )
        assert legacy_level.status_code == 201, legacy_level.text
        client.post(f"/api/v1/programs/{first['id']}/publish", headers=auth(token))
        client.post(f"/api/v1/programs/{second['id']}/publish", headers=auth(token))
        client.post(f"/api/v1/programs/{legacy_level.json()['id']}/publish", headers=auth(token))

        response = client.get("/api/v1/programs", params={"level": "engineering", "limit": 1})
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert client.get("/api/v1/programs", params={"level": "not-a-level"}).status_code == 422
        assert client.get("/api/v1/programs", params={"limit": 501}).status_code == 422
