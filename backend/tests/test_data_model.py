from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.models import (
    CandidateApplication,
    CandidateProfile,
    DocumentChunk,
    DocumentSource,
    DocumentSyncRun,
    Program,
    Recommendation,
    Role,
    User,
)
from app.seed_demo import seed_demo_data


def create_test_client() -> TestClient:
    return TestClient(create_app("sqlite://", auto_create_tables=True))


def test_relational_schema_links_candidate_application_and_documents() -> None:
    with create_test_client() as client:
        db = client.app.state.session_factory()
        try:
            user = User(
                email="schema@example.com",
                full_name="Schema Candidate",
                password_hash="not-used-in-this-test",
                role=Role.CANDIDATE.value,
            )
            program = Program(
                institution="IIT",
                name="Test programme",
                level="engineering",
                description="Test only",
            )
            db.add_all([user, program])
            db.flush()

            profile = CandidateProfile(user_id=user.id, graduation_year=2027, target_institution="IIT")
            application = CandidateApplication(
                candidate_user_id=user.id,
                program_id=program.id,
                academic_year="2027-2028",
            )
            source = DocumentSource(
                institution="IIT",
                title="Test source",
                original_filename="catalogue.pdf",
                storage_key="private/test/catalogue.pdf",
                checksum_sha256="a" * 64,
                content_type="application/pdf",
            )
            db.add_all([profile, application, source])
            db.flush()
            recommendation = Recommendation(
                application_id=application.id,
                program_id=program.id,
                score=0.8,
                explanation="Test recommendation",
            )
            chunk = DocumentChunk(document_source_id=source.id, chunk_index=0, content="Test content")
            sync = DocumentSyncRun(document_source_id=source.id, idempotency_key="test-sync-1")
            db.add_all([recommendation, chunk, sync])
            db.commit()

            assert db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id)) is not None
            assert db.scalar(select(CandidateApplication).where(CandidateApplication.candidate_user_id == user.id)) is not None
            assert db.scalar(select(Recommendation).where(Recommendation.application_id == application.id)) is not None
            assert db.scalar(select(DocumentChunk).where(DocumentChunk.document_source_id == source.id)) is not None
            assert db.scalar(select(DocumentSyncRun).where(DocumentSyncRun.document_source_id == source.id)) is not None

            application.status = "submitted"
            db.commit()
            assert application.version == 2

            db.add(Program(institution="OTHER", name="Invalid programme", level="other"))
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
        finally:
            db.close()


def test_database_rejects_applications_with_missing_references() -> None:
    with create_test_client() as client:
        db = client.app.state.session_factory()
        try:
            db.add(
                CandidateApplication(
                    candidate_user_id=uuid4(),
                    program_id=uuid4(),
                    academic_year="2027-2028",
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
        finally:
            db.close()


def test_demo_seed_is_idempotent_and_never_publishes_fake_programs() -> None:
    with create_test_client() as client:
        db = client.app.state.session_factory()
        try:
            assert seed_demo_data(db) == 4
            assert seed_demo_data(db) == 0
            programs = list(db.scalars(select(Program).where(Program.is_demo.is_(True))).all())
            assert len(programs) == 4
            assert all(not program.is_published for program in programs)
        finally:
            db.close()