from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(StrEnum):
    CANDIDATE = "candidate"
    ACADEMIC_IIT = "academic_iit"
    ACADEMIC_ISB = "academic_isb"
    INTERVIEWER = "interviewer"
    DIRECTION = "direction"
    ADMIN = "admin"


class Institution(StrEnum):
    IIT = "IIT"
    ISB = "ISB"


class ProgramLevel(StrEnum):
    PREPARATORY = "preparatory"
    BACHELOR = "bachelor"
    ENGINEERING = "engineering"
    OTHER = "other"
   

class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(32), default=Role.CANDIDATE.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    subject_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    previous_value: Mapped[str] = mapped_column(String(32))
    new_value: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = (
        CheckConstraint("institution IN ('IIT', 'ISB')", name="ck_programs_institution"),
        CheckConstraint(
            "level IN ('preparatory', 'bachelor', 'engineering', 'other')",
            name="ck_programs_level",
        ),
        UniqueConstraint("institution", "name", name="uq_programs_institution_name"),
        Index("ix_programs_institution_published", "institution", "is_published"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    institution: Mapped[str] = mapped_column(String(8), index=True)
    name: Mapped[str] = mapped_column(String(180))
    level: Mapped[str] = mapped_column(String(24))
    description: Mapped[str] = mapped_column(Text, default="")
    duration: Mapped[str | None] = mapped_column(String(80), nullable=True)
    admission_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    career_prospects: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    __table_args__ = (
        CheckConstraint(
            "target_institution IS NULL OR target_institution IN ('IIT', 'ISB')",
            name="ck_candidate_profiles_target_institution",
        ),
        CheckConstraint(
            "graduation_year IS NULL OR graduation_year BETWEEN 2000 AND 2200",
            name="ck_candidate_profiles_graduation_year",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    current_education: Mapped[str | None] = mapped_column(String(180), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_institution: Mapped[str | None] = mapped_column(String(8), nullable=True)
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class CandidateApplication(Base):
    __tablename__ = "candidate_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'under_review', 'interview_ready', 'accepted', 'rejected', 'withdrawn')",
            name="ck_candidate_applications_status",
        ),
        Index("ix_candidate_applications_status_created", "status", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    candidate_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    program_id: Mapped[UUID] = mapped_column(ForeignKey("programs.id", ondelete="RESTRICT"), index=True)
    academic_year: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'confirmed', 'adjusted', 'declined')",
            name="ck_recommendations_status",
        ),
        CheckConstraint("score IS NULL OR score BETWEEN 0 AND 1", name="ck_recommendations_score"),
        UniqueConstraint("application_id", "program_id", name="uq_recommendations_application_program"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidate_applications.id", ondelete="CASCADE"), index=True
    )
    program_id: Mapped[UUID] = mapped_column(ForeignKey("programs.id", ondelete="RESTRICT"), index=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    explanation: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="proposed", index=True)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class DocumentSource(Base):
    __tablename__ = "document_sources"
    __table_args__ = (
        CheckConstraint(
            "institution IS NULL OR institution IN ('IIT', 'ISB')",
            name="ck_document_sources_institution",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'withdrawn', 'processing', 'failed')",
            name="ck_document_sources_status",
        ),
        UniqueConstraint("storage_key", "version", name="uq_document_sources_storage_version"),
        Index("ix_document_sources_institution_status", "institution", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    institution: Mapped[str | None] = mapped_column(String(8), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512))
    source_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    content_type: Mapped[str] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    uploaded_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_source_id", "chunk_index", name="uq_document_chunks_source_index"),
        Index("ix_document_chunks_source_index", "document_source_id", "chunk_index"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_sources.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DocumentSyncRun(Base):
    __tablename__ = "document_sync_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_document_sync_runs_status",
        ),
        CheckConstraint("processed_count >= 0", name="ck_document_sync_runs_processed_count"),
        Index("ix_document_sync_runs_status_started", "status", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_sources.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)