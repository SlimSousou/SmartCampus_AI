import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from .config import settings


password_hasher = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = password_hasher.hash("not-a-real-user-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def verify_unknown_user_password(password: str) -> None:
    password_hasher.verify(password, _DUMMY_PASSWORD_HASH)


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iss": "smartcampus-ai",
        "aud": "smartcampus-api",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> UUID:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=["HS256"],
        audience="smartcampus-api",
        issuer="smartcampus-ai",
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    return UUID(payload["sub"])


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)