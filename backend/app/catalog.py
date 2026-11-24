from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import DbSession, OptionalUser, require_roles
from .catalog_schemas import (
    AdmissionConditionCreate,
    AdmissionConditionRead,
    AdmissionConditionUpdate,
    CurriculumCreate,
    CurriculumRead,
    CurriculumUpdate,
    FeeCreate,
    FeeRead,
    FeeUpdate,
    OfficialInfo,
    PaymentTermCreate,
    PaymentTermRead,
    PaymentTermUpdate,
    ProgramCreate,
    ProgramRead,
    ProgramUpdate,
    SpecialtyCreate,
    SpecialtyRead,
    SpecialtyUpdate,
    SubjectCreate,
    SubjectRead,
    SubjectUpdate,
)
from .models import (
    AdmissionCondition,
    Curriculum,
    Fee,
    Institution,
    PaymentTerm,
    Program,
    ProgramLevel,
    PublicationStatus,
    Role,
    Specialty,
    Subject,
    User,
    utc_now,
)


router = APIRouter(prefix="/api/v1", tags=["catalogue et informations officielles"])
ProgramEditor = Annotated[User, Depends(require_roles(Role.ACADEMIC_IIT, Role.ACADEMIC_ISB, Role.ADMIN))]

_INSTITUTION_BY_ROLE = {
    Role.ACADEMIC_IIT.value: "IIT",
    Role.ACADEMIC_ISB.value: "ISB",
}
_TUNISIA = timezone(timedelta(hours=1))


def _today() -> date:
    return datetime.now(_TUNISIA).date()


def _can_edit(user: User, institution: str) -> bool:
    if user.role == Role.ADMIN.value:
        return True
    return _INSTITUTION_BY_ROLE.get(user.role) == institution


def _require_program_editor(user: User, program: Program) -> None:
    if not _can_edit(user, program.institution):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez gérer que les formations de votre établissement.")


def _get_program(db: Session, program_id: UUID) -> Program:
    program = db.get(Program, program_id)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formation introuvable.")
    return program


def _get_specialty(db: Session, specialty_id: UUID) -> Specialty:
    item = db.get(Specialty, specialty_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spécialité introuvable.")
    return item


def _get_curriculum(db: Session, curriculum_id: UUID) -> Curriculum:
    item = db.get(Curriculum, curriculum_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme pédagogique introuvable.")
    return item


def _get_subject(db: Session, subject_id: UUID) -> Subject:
    item = db.get(Subject, subject_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matière introuvable.")
    return item


def _visible_catalog_children(user: User | None, program: Program, item_active: bool, include_inactive: bool) -> bool:
    if include_inactive and _can_view_inactive(user, program.institution):
        return True
    return program.is_published and not program.is_demo and item_active


def _require_curriculum_scope(db: Session, curriculum: Curriculum, user: User) -> Program:
    program = _get_program(db, curriculum.program_id)
    _require_program_editor(user, program)
    return program


def _validate_specialty(db: Session, program_id: UUID, specialty_id: UUID | None) -> None:
    if specialty_id is None:
        return
    specialty = _get_specialty(db, specialty_id)
    if specialty.program_id != program_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La spécialité doit appartenir à la même formation.")


def _check_subject_code(db: Session, curriculum_id: UUID, code: str | None, subject_id: UUID | None = None) -> None:
    if not code:
        return
    duplicate = db.scalar(
        select(Subject.id).where(
            Subject.curriculum_id == curriculum_id,
            func.lower(Subject.code) == code.lower(),
            Subject.id != (subject_id or UUID(int=0)),
        )
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce code matière existe déjà dans ce programme pédagogique.")


def _is_program_editor(user: User | None) -> bool:
    return bool(user and user.role in {*_INSTITUTION_BY_ROLE, Role.ADMIN.value})


def _public_program_query():
    return select(Program).where(Program.is_published.is_(True), Program.is_demo.is_(False))


def _official_predicates(model):
    today = _today()
    return (
        model.status == PublicationStatus.PUBLISHED.value,
        model.active.is_(True),
        or_(model.valid_from.is_(None), model.valid_from <= today),
        or_(model.valid_until.is_(None), model.valid_until >= today),
    )


def _official_query(model, program_id: UUID | None = None):
    query = select(model).join(Program, model.program_id == Program.id).where(
        Program.is_published.is_(True),
        Program.is_demo.is_(False),
        *_official_predicates(model),
    )
    if program_id is not None:
        query = query.where(model.program_id == program_id)
    return query


def _can_view_inactive(user: User | None, institution: str | None = None) -> bool:
    if user is None:
        return False
    if user.role == Role.ADMIN.value:
        return True
    own_institution = _INSTITUTION_BY_ROLE.get(user.role)
    return own_institution is not None and (institution is None or institution == own_institution)


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflit avec les données existantes.") from exc


def _ensure_program_exists(db: Session, program_id: UUID) -> Program:
    return _get_program(db, program_id)


def _check_period(start: date | None, end: date | None) -> None:
    if start and end and end < start:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La date de fin doit être postérieure ou égale à la date de début.")


def _overlaps(start_a: date | None, end_a: date | None, start_b: date | None, end_b: date | None) -> bool:
    min_date = date.min
    max_date = date.max
    return (start_a or min_date) <= (end_b or max_date) and (start_b or min_date) <= (end_a or max_date)


def _publish_official_item(db: Session, item, model, title_attribute: str, user: User) -> None:
    program = _ensure_program_exists(db, item.program_id)
    _require_program_editor(user, program)
    db.execute(select(Program.id).where(Program.id == program.id).with_for_update()).scalar_one()
    if not program.is_published or program.is_demo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Publiez d’abord une formation officielle.")
    if item.valid_until and item.valid_until < _today():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La période de validité est déjà terminée.")

    title = getattr(item, title_attribute)
    existing = db.scalars(
        select(model).where(
            model.program_id == item.program_id,
            model.id != item.id,
            model.status == PublicationStatus.PUBLISHED.value,
            model.active.is_(True),
            func.lower(getattr(model, title_attribute)) == title.lower(),
        )
    ).all()
    if any(_overlaps(item.valid_from, item.valid_until, other.valid_from, other.valid_until) for other in existing):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un élément officiel de même intitulé couvre déjà cette période.")

    item.status = PublicationStatus.PUBLISHED.value
    item.published_at = utc_now()


def _official_action(db: Session, item, model, title_attribute: str, action: str, user: User) -> None:
    if action not in {"publish", "archive", "draft"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action inconnue.")
    program = _ensure_program_exists(db, item.program_id)
    _require_program_editor(user, program)
    if action == "publish":
        _publish_official_item(db, item, model, title_attribute, user)
    elif action == "archive":
        item.status = PublicationStatus.ARCHIVED.value
    else:
        item.status = PublicationStatus.DRAFT.value
        item.published_at = None
    _commit(db)
    db.refresh(item)


@router.get("/programs", response_model=list[ProgramRead])
def list_programs(
    db: DbSession,
    user: OptionalUser,
    q: str | None = None,
    institution: Institution | None = None,
    level: ProgramLevel | None = None,
    include_inactive: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Program]:
    show_inactive = include_inactive and _can_view_inactive(user, institution)
    query = select(Program)
    if show_inactive:
        if user and user.role != Role.ADMIN.value:
            query = query.where(Program.institution == _INSTITUTION_BY_ROLE[user.role])
    else:
        query = query.where(Program.is_published.is_(True), Program.is_demo.is_(False))
    if institution:
        query = query.where(Program.institution == institution.value)
    if level:
        query = query.where(Program.level == level.value)
    if q and q.strip():
        pattern = f"%{q.strip().lower()}%"
        query = query.where(or_(func.lower(Program.name).like(pattern), func.lower(Program.description).like(pattern)))
    query = query.order_by(Program.institution, Program.name, Program.id).limit(limit).offset(offset)
    return list(db.scalars(query).all())


@router.get("/programs/{program_id}", response_model=ProgramRead)
def get_program(program_id: UUID, db: DbSession, user: OptionalUser, include_inactive: bool = False) -> Program:
    program = _get_program(db, program_id)
    if not (include_inactive and _can_view_inactive(user, program.institution)):
        if not program.is_published or program.is_demo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formation introuvable.")
    return program


@router.post("/programs", response_model=ProgramRead, status_code=status.HTTP_201_CREATED)
def create_program(payload: ProgramCreate, db: DbSession, user: ProgramEditor) -> Program:
    if not _can_edit(user, payload.institution.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez créer que des formations de votre établissement.")
    program = Program(**payload.model_dump(), is_published=False, is_demo=False)
    db.add(program)
    _commit(db)
    db.refresh(program)
    return program


@router.patch("/programs/{program_id}", response_model=ProgramRead)
def update_program(program_id: UUID, payload: ProgramUpdate, db: DbSession, user: ProgramEditor) -> Program:
    program = _get_program(db, program_id)
    _require_program_editor(user, program)
    changes = payload.model_dump(exclude_unset=True)
    nullable_fields = {"duration", "admission_requirements", "career_prospects"}
    for key, value in changes.items():
        if value is None and key not in nullable_fields:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{key} ne peut pas être null.")
        setattr(program, key, value.value if isinstance(value, Institution | ProgramLevel) else value)
    _require_program_editor(user, program)
    if changes and program.is_published:
        program.is_published = False
    _commit(db)
    db.refresh(program)
    return program


@router.post("/programs/{program_id}/{action}", response_model=ProgramRead)
def program_action(program_id: UUID, action: str, db: DbSession, user: ProgramEditor) -> Program:
    if action not in {"publish", "unpublish"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action inconnue.")
    program = _get_program(db, program_id)
    _require_program_editor(user, program)
    if action == "publish" and program.is_demo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une formation de démonstration ne peut pas être publiée.")
    program.is_published = action == "publish"
    _commit(db)
    db.refresh(program)
    return program


@router.delete("/programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program(program_id: UUID, db: DbSession, user: ProgramEditor) -> Response:
    program = _get_program(db, program_id)
    _require_program_editor(user, program)
    db.delete(program)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette formation est déjà référencée; désactivez-la au lieu de la supprimer.") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/specialties", response_model=list[SpecialtyRead])
def list_specialties(
    db: DbSession,
    user: OptionalUser,
    program_id: UUID | None = None,
    include_inactive: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Specialty]:
    query = select(Specialty).join(Program, Specialty.program_id == Program.id)
    if include_inactive and _can_view_inactive(user):
        if user and user.role != Role.ADMIN.value:
            query = query.where(Program.institution == _INSTITUTION_BY_ROLE[user.role])
    else:
        query = query.where(Program.is_published.is_(True), Program.is_demo.is_(False), Specialty.active.is_(True))
    if program_id is not None:
        query = query.where(Specialty.program_id == program_id)
    return list(db.scalars(query.order_by(Specialty.program_id, Specialty.name).limit(limit).offset(offset)).all())


@router.post("/specialties", response_model=SpecialtyRead, status_code=status.HTTP_201_CREATED)
def create_specialty(payload: SpecialtyCreate, db: DbSession, user: ProgramEditor) -> Specialty:
    _require_program_editor(user, _get_program(db, payload.program_id))
    item = Specialty(**payload.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.get("/specialties/{specialty_id}", response_model=SpecialtyRead)
def get_specialty(specialty_id: UUID, db: DbSession, user: OptionalUser, include_inactive: bool = False) -> Specialty:
    item = _get_specialty(db, specialty_id)
    if not _visible_catalog_children(user, _get_program(db, item.program_id), item.active, include_inactive):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spécialité introuvable.")
    return item


@router.patch("/specialties/{specialty_id}", response_model=SpecialtyRead)
def update_specialty(specialty_id: UUID, payload: SpecialtyUpdate, db: DbSession, user: ProgramEditor) -> Specialty:
    item = _get_specialty(db, specialty_id)
    _require_program_editor(user, _get_program(db, item.program_id))
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None and key != "description":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{key} ne peut pas être null.")
        setattr(item, key, value)
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/specialties/{specialty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_specialty(specialty_id: UUID, db: DbSession, user: ProgramEditor) -> Response:
    item = _get_specialty(db, specialty_id)
    _require_program_editor(user, _get_program(db, item.program_id))
    db.delete(item)
    _commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/curricula", response_model=list[CurriculumRead])
def list_curricula(
    db: DbSession,
    user: OptionalUser,
    program_id: UUID | None = None,
    specialty_id: UUID | None = None,
    include_inactive: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Curriculum]:
    query = select(Curriculum).join(Program, Curriculum.program_id == Program.id)
    if include_inactive and _can_view_inactive(user):
        if user and user.role != Role.ADMIN.value:
            query = query.where(Program.institution == _INSTITUTION_BY_ROLE[user.role])
    else:
        query = query.where(Program.is_published.is_(True), Program.is_demo.is_(False), Curriculum.active.is_(True))
        query = query.where(or_(Curriculum.specialty_id.is_(None), select(Specialty.active).where(Specialty.id == Curriculum.specialty_id).scalar_subquery().is_(True)))
    if program_id is not None:
        query = query.where(Curriculum.program_id == program_id)
    if specialty_id is not None:
        query = query.where(Curriculum.specialty_id == specialty_id)
    return list(db.scalars(query.order_by(Curriculum.program_id, Curriculum.name).limit(limit).offset(offset)).all())


@router.post("/curricula", response_model=CurriculumRead, status_code=status.HTTP_201_CREATED)
def create_curriculum(payload: CurriculumCreate, db: DbSession, user: ProgramEditor) -> Curriculum:
    _require_program_editor(user, _get_program(db, payload.program_id))
    _validate_specialty(db, payload.program_id, payload.specialty_id)
    item = Curriculum(**payload.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.get("/curricula/{curriculum_id}", response_model=CurriculumRead)
def get_curriculum(curriculum_id: UUID, db: DbSession, user: OptionalUser, include_inactive: bool = False) -> Curriculum:
    item = _get_curriculum(db, curriculum_id)
    program = _get_program(db, item.program_id)
    if not _visible_catalog_children(user, program, item.active, include_inactive):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme pédagogique introuvable.")
    if item.specialty_id:
        specialty = _get_specialty(db, item.specialty_id)
        if not _visible_catalog_children(user, program, specialty.active, include_inactive):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme pédagogique introuvable.")
    return item


@router.patch("/curricula/{curriculum_id}", response_model=CurriculumRead)
def update_curriculum(curriculum_id: UUID, payload: CurriculumUpdate, db: DbSession, user: ProgramEditor) -> Curriculum:
    item = _get_curriculum(db, curriculum_id)
    program = _require_curriculum_scope(db, item, user)
    changes = payload.model_dump(exclude_unset=True)
    if "specialty_id" in changes:
        _validate_specialty(db, program.id, changes["specialty_id"])
    for key, value in changes.items():
        if value is None and key not in {"specialty_id", "description", "academic_year"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{key} ne peut pas être null.")
        setattr(item, key, value)
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/curricula/{curriculum_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_curriculum(curriculum_id: UUID, db: DbSession, user: ProgramEditor) -> Response:
    item = _get_curriculum(db, curriculum_id)
    _require_curriculum_scope(db, item, user)
    db.delete(item)
    _commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/subjects", response_model=list[SubjectRead])
def list_subjects(
    db: DbSession,
    user: OptionalUser,
    program_id: UUID | None = None,
    curriculum_id: UUID | None = None,
    semester: int | None = Query(default=None, ge=1, le=12),
    include_inactive: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Subject]:
    query = select(Subject).join(Curriculum, Subject.curriculum_id == Curriculum.id).join(Program, Curriculum.program_id == Program.id)
    if include_inactive and _can_view_inactive(user):
        if user and user.role != Role.ADMIN.value:
            query = query.where(Program.institution == _INSTITUTION_BY_ROLE[user.role])
    else:
        query = query.where(Program.is_published.is_(True), Program.is_demo.is_(False), Curriculum.active.is_(True), Subject.active.is_(True))
    if program_id is not None:
        query = query.where(Curriculum.program_id == program_id)
    if curriculum_id is not None:
        query = query.where(Subject.curriculum_id == curriculum_id)
    if semester is not None:
        query = query.where(Subject.semester == semester)
    return list(db.scalars(query.order_by(Subject.curriculum_id, Subject.semester, Subject.name).limit(limit).offset(offset)).all())


@router.post("/subjects", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
def create_subject(payload: SubjectCreate, db: DbSession, user: ProgramEditor) -> Subject:
    curriculum = _get_curriculum(db, payload.curriculum_id)
    _require_curriculum_scope(db, curriculum, user)
    _check_subject_code(db, curriculum.id, payload.code)
    item = Subject(**payload.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.get("/subjects/{subject_id}", response_model=SubjectRead)
def get_subject(subject_id: UUID, db: DbSession, user: OptionalUser, include_inactive: bool = False) -> Subject:
    item = _get_subject(db, subject_id)
    curriculum = _get_curriculum(db, item.curriculum_id)
    program = _get_program(db, curriculum.program_id)
    if not _visible_catalog_children(user, program, curriculum.active and item.active, include_inactive):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matière introuvable.")
    return item


@router.patch("/subjects/{subject_id}", response_model=SubjectRead)
def update_subject(subject_id: UUID, payload: SubjectUpdate, db: DbSession, user: ProgramEditor) -> Subject:
    item = _get_subject(db, subject_id)
    old_curriculum = _get_curriculum(db, item.curriculum_id)
    _require_curriculum_scope(db, old_curriculum, user)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("curriculum_id", item.curriculum_id) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="curriculum_id ne peut pas être null.")
    if "name" in changes and changes["name"] is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="name ne peut pas être null.")
    new_curriculum = _get_curriculum(db, changes.get("curriculum_id", item.curriculum_id))
    _require_curriculum_scope(db, new_curriculum, user)
    _check_subject_code(db, new_curriculum.id, changes.get("code", item.code), item.id)
    for key, value in changes.items():
        if value is None and key not in {"code", "semester", "credits", "coefficient", "hours", "description"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{key} ne peut pas être null.")
        setattr(item, key, value)
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: UUID, db: DbSession, user: ProgramEditor) -> Response:
    item = _get_subject(db, subject_id)
    _require_curriculum_scope(db, _get_curriculum(db, item.curriculum_id), user)
    db.delete(item)
    _commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/fees", response_model=list[FeeRead])
def list_fees(
    db: DbSession,
    user: OptionalUser,
    program_id: UUID | None = None,
    institution: str | None = Query(default=None, pattern="^(IIT|ISB)$"),
    include_inactive: bool = False,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(draft|published|archived)$"),
    validity: str | None = Query(default=None, pattern="^(current|upcoming|expired)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Fee]:
    show_inactive = include_inactive and _can_view_inactive(user, institution)
    query = select(Fee).join(Program, Fee.program_id == Program.id)
    if show_inactive:
        if user and user.role != Role.ADMIN.value:
            query = query.where(Program.institution == _INSTITUTION_BY_ROLE[user.role])
        if status_filter:
            query = query.where(Fee.status == status_filter)
    else:
        query = query.where(Program.is_published.is_(True), Program.is_demo.is_(False), *_official_predicates(Fee))
    if program_id is not None:
        query = query.where(Fee.program_id == program_id)
    if institution:
        query = query.where(Program.institution == institution)
    if validity:
        today = _today()
        if validity == "current":
            query = query.where(*_official_predicates(Fee))
        elif validity == "upcoming":
            query = query.where(Fee.valid_from > today)
        else:
            query = query.where(Fee.valid_until < today)
    return list(db.scalars(query.order_by(Fee.program_id, Fee.label, Fee.id).limit(limit).offset(offset)).all())


def _official_predicates(model):
    today = _today()
    return (
        model.status == PublicationStatus.PUBLISHED.value,
        model.active.is_(True),
        or_(model.valid_from.is_(None), model.valid_from <= today),
        or_(model.valid_until.is_(None), model.valid_until >= today),
    )


def _get_fee(db: Session, fee_id: UUID) -> Fee:
    fee = db.get(Fee, fee_id)
    if fee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarif introuvable.")
    return fee


def _get_admission_condition(db: Session, condition_id: UUID) -> AdmissionCondition:
    item = db.get(AdmissionCondition, condition_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition d’admission introuvable.")
    return item


def _get_payment_term(db: Session, term_id: UUID) -> PaymentTerm:
    item = db.get(PaymentTerm, term_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modalité de paiement introuvable.")
    return item


def _visible_official_item(item, program: Program, user: User | None, include_inactive: bool) -> bool:
    if include_inactive and _can_view_inactive(user, program.institution):
        return True
    return bool(
        program.is_published
        and not program.is_demo
        and item.status == PublicationStatus.PUBLISHED.value
        and item.active
        and (item.valid_from is None or item.valid_from <= _today())
        and (item.valid_until is None or item.valid_until >= _today())
    )


def _apply_changes(obj, changes: dict, nullable_fields: set[str]) -> None:
    for key, value in changes.items():
        if value is None and key not in nullable_fields:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{key} ne peut pas être null.")
        setattr(obj, key, value)


def _change_official_content(obj, changes: dict) -> None:
    if changes and obj.status == PublicationStatus.PUBLISHED.value and set(changes) - {"active"}:
        obj.status = PublicationStatus.DRAFT.value
        obj.published_at = None


def _validate_payment_term_fee(db: Session, program_id: UUID, fee_id: UUID | None) -> None:
    if fee_id is None:
        return
    fee = db.get(Fee, fee_id)
    if fee is None or fee.program_id != program_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le tarif référencé doit appartenir à la même formation.",
        )


@router.post("/fees", response_model=FeeRead, status_code=status.HTTP_201_CREATED)
def create_fee(payload: FeeCreate, db: DbSession, user: ProgramEditor) -> Fee:
    program = _ensure_program_exists(db, payload.program_id)
    _require_program_editor(user, program)
    fee = Fee(**payload.model_dump(), status=PublicationStatus.DRAFT.value, active=True)
    db.add(fee)
    _commit(db)
    db.refresh(fee)
    return fee


@router.get("/fees/{fee_id}", response_model=FeeRead)
def get_fee(fee_id: UUID, db: DbSession, user: OptionalUser, include_inactive: bool = False) -> Fee:
    fee = _get_fee(db, fee_id)
    program = _get_program(db, fee.program_id)
    if not _visible_official_item(fee, program, user, include_inactive):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarif introuvable.")
    return fee


@router.patch("/fees/{fee_id}", response_model=FeeRead)
def update_fee(fee_id: UUID, payload: FeeUpdate, db: DbSession, user: ProgramEditor) -> Fee:
    fee = _get_fee(db, fee_id)
    _require_program_editor(user, _get_program(db, fee.program_id))
    changes = payload.model_dump(exclude_unset=True)
    _apply_changes(fee, changes, {"description", "academic_year", "valid_from", "valid_until"})
    _change_official_content(fee, changes)
    _commit(db)
    db.refresh(fee)
    return fee


@router.post("/fees/{fee_id}/{action}", response_model=FeeRead)
def fee_action(fee_id: UUID, action: str, db: DbSession, user: ProgramEditor) -> Fee:
    fee = _get_fee(db, fee_id)
    _official_action(db, fee, Fee, "label", action, user)
    return fee


@router.delete("/fees/{fee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fee(fee_id: UUID, db: DbSession, user: ProgramEditor) -> Response:
    fee = _get_fee(db, fee_id)
    _require_program_editor(user, _get_program(db, fee.program_id))
    db.delete(fee)
    _commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/admission-conditions", response_model=list[AdmissionConditionRead])
def list_admission_conditions(
    db: DbSession,
    user: OptionalUser,
    program_id: UUID | None = None,
    institution: str | None = Query(default=None, pattern="^(IIT|ISB)$"),
    include_inactive: bool = False,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(draft|published|archived)$"),
    validity: str | None = Query(default=None, pattern="^(current|upcoming|expired)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AdmissionCondition]:
    show_inactive = include_inactive and _can_view_inactive(user, institution)
    query = select(AdmissionCondition).join(Program, AdmissionCondition.program_id == Program.id)
    if show_inactive:
        if user and user.role != Role.ADMIN.value:
            query = query.where(Program.institution == _INSTITUTION_BY_ROLE[user.role])
        if status_filter:
            query = query.where(AdmissionCondition.status == status_filter)
    else:
        query = query.where(
            Program.is_published.is_(True),
            Program.is_demo.is_(False),
            *_official_predicates(AdmissionCondition),
        )
    if program_id is not None:
        query = query.where(AdmissionCondition.program_id == program_id)
    if institution:
        query = query.where(Program.institution == institution)
    if validity:
        today = _today()
        if validity == "current":
            query = query.where(*_official_predicates(AdmissionCondition))
        elif validity == "upcoming":
            query = query.where(AdmissionCondition.valid_from > today)
        else:
            query = query.where(AdmissionCondition.valid_until < today)
    return list(
        db.scalars(
            query.order_by(AdmissionCondition.program_id, AdmissionCondition.title, AdmissionCondition.id)
            .limit(limit)
            .offset(offset)
        ).all()
    )


@router.post("/admission-conditions", response_model=AdmissionConditionRead, status_code=status.HTTP_201_CREATED)
def create_admission_condition(payload: AdmissionConditionCreate, db: DbSession, user: ProgramEditor) -> AdmissionCondition:
    program = _ensure_program_exists(db, payload.program_id)
    _require_program_editor(user, program)
    item = AdmissionCondition(**payload.model_dump(), status=PublicationStatus.DRAFT.value, active=True)
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.get("/admission-conditions/{condition_id}", response_model=AdmissionConditionRead)
def get_admission_condition(
    condition_id: UUID,
    db: DbSession,
    user: OptionalUser,
    include_inactive: bool = False,
) -> AdmissionCondition:
    item = _get_admission_condition(db, condition_id)
    program = _get_program(db, item.program_id)
    if not _visible_official_item(item, program, user, include_inactive):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition d’admission introuvable.")
    return item


@router.patch("/admission-conditions/{condition_id}", response_model=AdmissionConditionRead)
def update_admission_condition(
    condition_id: UUID,
    payload: AdmissionConditionUpdate,
    db: DbSession,
    user: ProgramEditor,
) -> AdmissionCondition:
    item = _get_admission_condition(db, condition_id)
    _require_program_editor(user, _get_program(db, item.program_id))
    changes = payload.model_dump(exclude_unset=True)
    _apply_changes(item, changes, {"description", "threshold", "academic_year", "valid_from", "valid_until"})
    _change_official_content(item, changes)
    _commit(db)
    db.refresh(item)
    return item


@router.post("/admission-conditions/{condition_id}/{action}", response_model=AdmissionConditionRead)
def admission_condition_action(
    condition_id: UUID,
    action: str,
    db: DbSession,
    user: ProgramEditor,
) -> AdmissionCondition:
    item = _get_admission_condition(db, condition_id)
    _official_action(db, item, AdmissionCondition, "title", action, user)
    return item


@router.delete("/admission-conditions/{condition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admission_condition(condition_id: UUID, db: DbSession, user: ProgramEditor) -> Response:
    item = _get_admission_condition(db, condition_id)
    _require_program_editor(user, _get_program(db, item.program_id))
    db.delete(item)
    _commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/payment-terms", response_model=list[PaymentTermRead])
def list_payment_terms(
    db: DbSession,
    user: OptionalUser,
    program_id: UUID | None = None,
    include_inactive: bool = False,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(draft|published|archived)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[PaymentTerm]:
    show_inactive = include_inactive and _can_view_inactive(user)
    query = select(PaymentTerm).join(Program, PaymentTerm.program_id == Program.id)
    if show_inactive:
        if user and user.role != Role.ADMIN.value:
            query = query.where(Program.institution == _INSTITUTION_BY_ROLE[user.role])
        if status_filter:
            query = query.where(PaymentTerm.status == status_filter)
    else:
        query = query.where(Program.is_published.is_(True), Program.is_demo.is_(False), *_official_predicates(PaymentTerm))
    if program_id is not None:
        query = query.where(PaymentTerm.program_id == program_id)
    return list(db.scalars(query.order_by(PaymentTerm.program_id, PaymentTerm.title, PaymentTerm.id).limit(limit).offset(offset)).all())


@router.post("/payment-terms", response_model=PaymentTermRead, status_code=status.HTTP_201_CREATED)
def create_payment_term(payload: PaymentTermCreate, db: DbSession, user: ProgramEditor) -> PaymentTerm:
    program = _ensure_program_exists(db, payload.program_id)
    _require_program_editor(user, program)
    _validate_payment_term_fee(db, payload.program_id, payload.fee_id)
    item = PaymentTerm(**payload.model_dump(), status=PublicationStatus.DRAFT.value, active=True)
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.get("/payment-terms/{term_id}", response_model=PaymentTermRead)
def get_payment_term(term_id: UUID, db: DbSession, user: OptionalUser, include_inactive: bool = False) -> PaymentTerm:
    item = _get_payment_term(db, term_id)
    program = _get_program(db, item.program_id)
    if not _visible_official_item(item, program, user, include_inactive):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modalité de paiement introuvable.")
    return item


@router.patch("/payment-terms/{term_id}", response_model=PaymentTermRead)
def update_payment_term(term_id: UUID, payload: PaymentTermUpdate, db: DbSession, user: ProgramEditor) -> PaymentTerm:
    item = _get_payment_term(db, term_id)
    _require_program_editor(user, _get_program(db, item.program_id))
    changes = payload.model_dump(exclude_unset=True)
    fee_id = changes.get("fee_id", item.fee_id)
    _validate_payment_term_fee(db, item.program_id, fee_id)
    _apply_changes(item, changes, {"description", "down_payment_percent", "due_date", "academic_year", "valid_from", "valid_until", "fee_id"})
    _change_official_content(item, changes)
    _commit(db)
    db.refresh(item)
    return item


@router.post("/payment-terms/{term_id}/{action}", response_model=PaymentTermRead)
def payment_term_action(term_id: UUID, action: str, db: DbSession, user: ProgramEditor) -> PaymentTerm:
    item = _get_payment_term(db, term_id)
    _official_action(db, item, PaymentTerm, "title", action, user)
    return item


@router.delete("/payment-terms/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_term(term_id: UUID, db: DbSession, user: ProgramEditor) -> Response:
    item = _get_payment_term(db, term_id)
    _require_program_editor(user, _get_program(db, item.program_id))
    db.delete(item)
    _commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _official_items_for_program(db: Session, model, program_id: UUID):
    return list(db.scalars(_official_query(model, program_id).order_by(model.id)).all())


@router.get("/programs/{program_id}/official-info", response_model=OfficialInfo)
def get_program_official_info(
    program_id: UUID,
    db: DbSession,
    user: OptionalUser,
    include_inactive: bool = False,
) -> OfficialInfo:
    program = _get_program(db, program_id)
    if not (include_inactive and _can_view_inactive(user, program.institution)) and (
        not program.is_published or program.is_demo
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formation introuvable.")
    fees = _official_items_for_program(db, Fee, program_id)
    payment_terms = _official_items_for_program(db, PaymentTerm, program_id)
    conditions = _official_items_for_program(db, AdmissionCondition, program_id)
    return OfficialInfo(
        program=program,
        as_of=_today(),
        fees=fees,
        payment_terms=payment_terms,
        admission_conditions=conditions,
        complete={"fees": bool(fees), "payment_terms": bool(payment_terms), "admission_conditions": bool(conditions)},
    )
