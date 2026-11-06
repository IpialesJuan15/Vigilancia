import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, Response
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify_password(hashed: str | None, password: str) -> bool:
    try:
        return hasher.verify(hashed or DUMMY_HASH, password) and hashed is not None
    except (VerificationError, InvalidHashError):
        return False


def csrf_guard(request: Request):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if request.headers.get("origin") != get_settings().app_base_url:
            raise HTTPException(403, "Origen de la solicitud no permitido")
        supplied = request.headers.get("x-csrf-token", "")
        cookie = request.cookies.get("csrf_token", "")
        if not cookie or not secrets.compare_digest(cookie, supplied):
            raise HTTPException(403, "Recarga la página para continuar de forma segura")


def set_session(response: Response, user: User):
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": user.id,
            "ver": user.session_version,
            "kind": "session",
            "exp": datetime.now(UTC) + timedelta(minutes=settings.session_minutes),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    response.set_cookie(
        "session",
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_minutes * 60,
        path="/",
    )


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(
            request.cookies.get("session", ""),
            get_settings().jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "ver"]},
        )
        user = db.get(User, payload["sub"])
        if not user or payload.get("kind") != "session" or payload["ver"] != user.session_version:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Inicia sesión para continuar") from None


def require_roles(*roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Tu cuenta no tiene permiso para esta acción")
        return user

    return dependency


def rate_limit(request: Request, scope: str, limit: int = 10, seconds: int = 900):
    # Use the direct peer; never trust arbitrary forwarded headers.
    address = request.client.host if request.client else "unknown"
    key = f"rate:{scope}:{digest(address)}"
    try:
        client = Redis.from_url(get_settings().redis_url)
        count = client.eval(
            "local n=redis.call('INCR',KEYS[1]); "
            "if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n",
            1,
            key,
            seconds,
        )
        if int(count) > limit:
            raise HTTPException(
                429,
                "Demasiados intentos. Inténtalo más tarde",
                headers={"Retry-After": str(seconds)},
            )
    except RedisError:
        raise HTTPException(503, "El servicio de acceso no está disponible temporalmente") from None
