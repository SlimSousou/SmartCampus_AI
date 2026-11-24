from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import Institution, ProgramLevel


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _validate_period(valid_from: date | None, valid_until: date | None) -> None:
    if valid_from and valid_until and valid_until < valid_from:
        raise ValueError("valid_until must not be before valid_from")


def _validate_academic_year(academic_year: str | None) -> str | None:
    if academic_year is None:
        return None
    parts = academic_year.split("-")
    if len(parts) != 2 or not all(part.isdigit() and len(part) == 4 for part in parts):
        raise ValueError("academic_year must look like 2026-2027")
    if int(parts[1]) != int(parts[0]) + 1:
        raise ValueError("academic_year must contain consecutive years")
    return academic_year


class ProgramCreate(StrictInput):
    institution: Institution
    level: ProgramLevel
    name: str = Field(min_length=1, max_length=180)
    description: str = ""
    duration: str | None = Field(default=None, max_length=80)
    admission_requirements: str | None = None
    career_prospects: str | None = None


class ProgramUpdate(StrictInput):
    institution: Institution | None = None
    level: ProgramLevel | None = None
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    duration: str | None = Field(default=None, max_length=80)
    admission_requirements: str | None = None
    career_prospects: str | None = None


class ProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution: Institution
    level: ProgramLevel
    name: str
    description: str
    duration: str | None
    admission_requirements: str | None
    career_prospects: str | None
    is_published: bool
    is_demo: bool


class SpecialtyCreate(StrictInput):
    program_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


class SpecialtyUpdate(StrictInput):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    active: bool | None = None


class SpecialtyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    name: str
    description: str
    active: bool


class CurriculumCreate(StrictInput):
    program_id: UUID
    specialty_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    description: str = ""

    @model_validator(mode="after")
    def validate_curriculum_year(self) -> "CurriculumCreate":
        _validate_academic_year(self.academic_year)
        return self


class CurriculumUpdate(StrictInput):
    specialty_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    description: str | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def validate_curriculum_year(self) -> "CurriculumUpdate":
        _validate_academic_year(self.academic_year)
        return self


class CurriculumRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    specialty_id: UUID | None
    name: str
    academic_year: str | None
    description: str
    active: bool


class SubjectCreate(StrictInput):
    curriculum_id: UUID
    code: str | None = Field(default=None, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    semester: int | None = Field(default=None, ge=1, le=12)
    credits: Decimal | None = Field(default=None, ge=0, le=60, max_digits=6, decimal_places=2)
    coefficient: Decimal | None = Field(default=None, ge=0, le=20, max_digits=6, decimal_places=2)
    hours: Decimal | None = Field(default=None, ge=0, le=2000, max_digits=8, decimal_places=2)
    description: str = ""


class SubjectUpdate(StrictInput):
    curriculum_id: UUID | None = None
    code: str | None = Field(default=None, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    semester: int | None = Field(default=None, ge=1, le=12)
    credits: Decimal | None = Field(default=None, ge=0, le=60, max_digits=6, decimal_places=2)
    coefficient: Decimal | None = Field(default=None, ge=0, le=20, max_digits=6, decimal_places=2)
    hours: Decimal | None = Field(default=None, ge=0, le=2000, max_digits=8, decimal_places=2)
    description: str | None = None
    active: bool | None = None


class SubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    curriculum_id: UUID
    code: str | None
    name: str
    semester: int | None
    credits: Decimal | None
    coefficient: Decimal | None
    hours: Decimal | None
    description: str
    active: bool


class FeeCreate(StrictInput):
    program_id: UUID
    label: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    currency: str = Field(default="TND", pattern=r"^[A-Z]{3}$")
    period: Literal["annual", "semester", "one_time"]
    description: str = ""
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    valid_from: date | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def validate_fee_period(self) -> "FeeCreate":
        _validate_period(self.valid_from, self.valid_until)
        _validate_academic_year(self.academic_year)
        return self


class FeeUpdate(StrictInput):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    period: Literal["annual", "semester", "one_time"] | None = None
    description: str | None = None
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    valid_from: date | None = None
    valid_until: date | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def validate_fee_period(self) -> "FeeUpdate":
        _validate_period(self.valid_from, self.valid_until)
        _validate_academic_year(self.academic_year)
        return self


class FeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    label: str
    amount: Decimal
    currency: str
    period: str
    description: str
    academic_year: str | None
    valid_from: date | None
    valid_until: date | None
    status: str
    active: bool
    published_at: datetime | None


AdmissionKind = Literal["diploma", "average", "document", "exam", "language", "age", "other"]


class AdmissionConditionCreate(StrictInput):
    program_id: UUID
    kind: AdmissionKind
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    required: bool = True
    threshold: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=3)
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    valid_from: date | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def validate_condition_period(self) -> "AdmissionConditionCreate":
        _validate_period(self.valid_from, self.valid_until)
        _validate_academic_year(self.academic_year)
        return self


class AdmissionConditionUpdate(StrictInput):
    kind: AdmissionKind | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    required: bool | None = None
    threshold: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=3)
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    valid_from: date | None = None
    valid_until: date | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def validate_condition_period(self) -> "AdmissionConditionUpdate":
        _validate_period(self.valid_from, self.valid_until)
        _validate_academic_year(self.academic_year)
        return self


class AdmissionConditionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    kind: str
    title: str
    description: str
    required: bool
    threshold: Decimal | None
    academic_year: str | None
    valid_from: date | None
    valid_until: date | None
    status: str
    active: bool
    published_at: datetime | None


class PaymentTermCreate(StrictInput):
    program_id: UUID
    fee_id: UUID | None = None
    method: Literal["bank_transfer", "cash", "cheque", "card", "online", "other"]
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    installments: int = Field(default=1, ge=1, le=36)
    down_payment_percent: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    due_date: date | None = None
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    valid_from: date | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def validate_payment_period(self) -> "PaymentTermCreate":
        _validate_period(self.valid_from, self.valid_until)
        _validate_academic_year(self.academic_year)
        return self


class PaymentTermUpdate(StrictInput):
    fee_id: UUID | None = None
    method: Literal["bank_transfer", "cash", "cheque", "card", "online", "other"] | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    installments: int | None = Field(default=None, ge=1, le=36)
    down_payment_percent: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    due_date: date | None = None
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    valid_from: date | None = None
    valid_until: date | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def validate_payment_period(self) -> "PaymentTermUpdate":
        _validate_period(self.valid_from, self.valid_until)
        _validate_academic_year(self.academic_year)
        return self


class PaymentTermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    fee_id: UUID | None
    method: str
    title: str
    description: str
    installments: int
    down_payment_percent: Decimal | None
    due_date: date | None
    academic_year: str | None
    valid_from: date | None
    valid_until: date | None
    status: str
    active: bool
    published_at: datetime | None


class OfficialInfo(BaseModel):
    program: ProgramRead
    as_of: date
    fees: list[FeeRead]
    payment_terms: list[PaymentTermRead]
    admission_conditions: list[AdmissionConditionRead]
    complete: dict[str, bool]
