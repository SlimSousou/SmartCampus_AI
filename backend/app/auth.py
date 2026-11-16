import secrets
from datetime import timedelta
from typing import Annotated, Callable
from uuid import UUID, uuid4

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import AuditEvent, RefreshSession, Role, User, utc_now
from .schemas import LoginRequest, RegisterRequest, RoleUpdateRequest, TokenResponse, UserRead
from .security import (
    create_access_token,
    create_csrf_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_unknown_user_password,
)


router = APIRouter(prefix="/api/v1", tags=["authentication and roles"])
bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _set_refresh_cookies(response: Response, refresh_token: str, csrf_token: str) -> None:
    max_age = settings.refresh_token_days * 24 * 60 * 60
    cookie_options = {
        "max_age": max_age,
        "secure": settings.cookie_secure,
        "samesite": "strict",
        "path": "/api/v1/auth",
    }
    response.set_cookie("sc_refresh", refresh_token, httponly=True, **cookie_options)
    response.set_cookie("sc_csrf", csrf_token, httponly=False, **cookie_options)


def _clear_refresh_cookies(response: Response) -> None:
    response.delete_cookie("sc_refresh", path="/api/v1/auth", secure=settings.cookie_secure, httponly=True, samesite="strict")
    response.delete_cookie("sc_csrf", path="/api/v1/auth", secure=settings.cookie_secure, httponly=False, samesite="strict")


def _issue_refresh_session(db: Session, user_id: UUID, family_id: UUID | None = None) -> str:
    token = create_refresh_token()
    db.add(
        RefreshSession(
            user_id=user_id,
            family_id=family_id or uuid4(),
            token_hash=hash_refresh_token(token),
            expires_at=utc_now() + timedelta(days=settings.refresh_token_days),
        )
    )
    return token


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    if credentials is None:
        raise _unauthorized()
    try:
        user_id = decode_access_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise _unauthorized() from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[[CurrentUser], User]:
    def check_role(user: CurrentUser) -> User:
        if user.role not in {role.value for role in roles}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission insuffisante.")
        return user

    return check_role


@router.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> User:
    user = User(
        email=str(payload.email).strip().lower(),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=Role.CANDIDATE.value,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un compte utilise déjà cette adresse.") from None
    db.refresh(user)
    return user


def _login_user(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        verify_unknown_user_password(password)
        raise _unauthorized()
    if not verify_password(password, user.password_hash) or not user.is_active:
        raise _unauthorized()
    return user


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.access_token_minutes * 60,
    )


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: DbSession) -> TokenResponse:
    user = _login_user(db, str(payload.email), payload.password)
    refresh_token = _issue_refresh_session(db, user.id)
    db.commit()
    _set_refresh_cookies(response, refresh_token, create_csrf_token())
    return _token_response(user)


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    db: DbSession,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> TokenResponse:
    refresh_token = request.cookies.get("sc_refresh")
    csrf_cookie = request.cookies.get("sc_csrf")
    if not refresh_token or not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
        raise _unauthorized()

    stored = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_refresh_token(refresh_token)))
    if stored is None:
        raise _unauthorized()
    if stored.revoked_at is not None:
        db.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == stored.family_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        db.commit()
        raise _unauthorized()
    if stored.expires_at <= utc_now():
        stored.revoked_at = utc_now()
        db.commit()
        raise _unauthorized()

    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        stored.revoked_at = utc_now()
        db.commit()
        raise _unauthorized()

    rotation = db.execute(
        update(RefreshSession)
        .where(RefreshSession.id == stored.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=utc_now())
    )
    if rotation.rowcount != 1:
        db.rollback()
        db.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == stored.family_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        db.commit()
        raise _unauthorized()
    next_refresh_token = _issue_refresh_session(db, user.id, stored.family_id)
    db.commit()
    _set_refresh_cookies(response, next_refresh_token, create_csrf_token())
    return _token_response(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession, user: CurrentUser) -> Response:
    refresh_token = request.cookies.get("sc_refresh")
    if refresh_token:
        stored = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_refresh_token(refresh_token)))
        if stored is not None and stored.user_id == user.id and stored.revoked_at is None:
            stored.revoked_at = utc_now()
            db.commit()
    _clear_refresh_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user


@router.get("/admin/users", response_model=list[UserRead])
def list_users(
    db: DbSession,
    _: Annotated[User, Depends(require_roles(Role.ADMIN))],
    limit: int = 20,
) -> list[User]:
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit doit être entre 1 et 100.")
    return list(db.scalars(select(User).order_by(User.created_at.desc()).limit(limit)).all())


@router.patch("/admin/users/{user_id}/roles", response_model=UserRead)
def update_user_role(
    user_id: UUID,
    payload: RoleUpdateRequest,
    db: DbSession,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN))],
) -> User:
    subject = db.get(User, user_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    if subject.id == actor.id and payload.role != Role.ADMIN:
        admin_count = db.scalar(
            select(func.count()).select_from(User).where(User.role == Role.ADMIN.value, User.is_active.is_(True))
        )
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Impossible de retirer le dernier rôle administrateur actif.")

    previous_role = subject.role
    subject.role = payload.role.value
    db.add(
        AuditEvent(
            actor_user_id=actor.id,
            subject_user_id=subject.id,
            action="user.role_changed",
            previous_value=previous_role,
            new_value=subject.role,
        )
    )
    db.commit()
    db.refresh(subject)
    return subject