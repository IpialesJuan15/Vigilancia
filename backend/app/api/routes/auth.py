import re
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User
from app.schemas import EmailInput, Login, PasswordReset, Register, TokenInput, UserOut
from app.security import (
    current_user,
    hasher,
    rate_limit,
    set_session,
    verify_password,
)
from app.services.auth import audit, consume_token, issue_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])
GENERIC = {"message": "Si el correo puede recibir este mensaje, enviaremos un enlace"}


@router.get("/csrf")
def csrf(response: Response):
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        "csrf_token",
        token,
        secure=get_settings().cookie_secure,
        samesite="lax",
        httponly=True,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"token": token}


@router.get("/capabilities")
def capabilities():
    settings = get_settings()
    return {"orcid": bool(settings.orcid_client_id and settings.orcid_client_secret)}


@router.post("/register", status_code=202)
def register(data: Register, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "register", 5)
    if db.scalar(select(User).where(User.email == data.email)):
        return GENERIC
    user = User(email=data.email, name=data.name, password_hash=hasher.hash(data.password))
    db.add(user)
    try:
        db.flush()
        audit(db, user, "registered")
        db.commit()
    except IntegrityError:
        db.rollback()
        return GENERIC
    issue_token(db, user, "verify")
    return GENERIC


@router.post("/verify-email")
def verify_email(data: TokenInput, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "verify", 20)
    user = consume_token(db, data.token, "verify")
    user.email_verified = True
    audit(db, user, "email_verified")
    db.commit()
    return {"message": "Correo verificado. Ya puedes iniciar sesión"}


@router.post("/verification/resend", status_code=202)
def resend(data: EmailInput, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "resend", 5)
    user = db.scalar(select(User).where(User.email == data.email))
    if user and not user.email_verified:
        issue_token(db, user, "verify")
    return GENERIC


@router.post("/login", response_model=UserOut)
def login(data: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, "login")
    user = db.scalar(select(User).where(User.email == data.email))
    if not verify_password(user.password_hash if user else None, data.password) or not user:
        raise HTTPException(401, "Correo o contraseña incorrectos")
    if not user.email_verified:
        raise HTTPException(403, "Verifica tu correo antes de iniciar sesión")
    audit(db, user, "login")
    db.commit()
    set_session(response, user)
    return user


@router.post("/logout")
def logout(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.session_version += 1
    audit(db, user, "logout")
    db.commit()
    response.delete_cookie(
        "session", path="/", secure=get_settings().cookie_secure, httponly=True, samesite="lax"
    )
    return {"message": "Sesión cerrada"}


@router.post("/password/forgot", status_code=202)
def forgot(data: EmailInput, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "forgot", 5)
    user = db.scalar(select(User).where(User.email == data.email))
    if user and user.email_verified and user.password_hash:
        issue_token(db, user, "reset")
    return GENERIC


@router.post("/password/reset")
def reset(data: PasswordReset, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "reset", 10)
    user = consume_token(db, data.token, "reset")
    user.password_hash = hasher.hash(data.password)
    user.session_version += 1
    audit(db, user, "password_reset")
    db.commit()
    return {"message": "Contraseña restablecida. Inicia sesión de nuevo"}


@router.get("/orcid/login")
def orcid_login(request: Request):
    rate_limit(request, "orcid", 20)
    settings = get_settings()
    if not settings.orcid_client_id or not settings.orcid_client_secret:
        raise HTTPException(503, "El acceso con ORCID todavía no está configurado")
    state = secrets.token_urlsafe(32)
    signed = jwt.encode(
        {"state": state, "kind": "oauth", "exp": datetime.now(UTC) + timedelta(minutes=10)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    query = urlencode(
        {
            "client_id": settings.orcid_client_id,
            "response_type": "code",
            "scope": "/authenticate",
            "redirect_uri": settings.orcid_redirect_uri,
            "state": state,
        }
    )
    response = RedirectResponse("https://sandbox.orcid.org/oauth/authorize?" + query)
    response.set_cookie(
        "oauth_state",
        signed,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=600,
        path="/",
    )
    return response


@router.get("/orcid/callback")
def orcid_callback(
    request: Request, code: str = "", state: str = "", db: Session = Depends(get_db)
):
    settings = get_settings()
    try:
        payload = jwt.decode(
            request.cookies.get("oauth_state", ""),
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "state", "kind"]},
        )
        if payload["kind"] != "oauth" or not secrets.compare_digest(payload["state"], state):
            raise ValueError()
        if not code or not settings.orcid_client_id or not settings.orcid_client_secret:
            raise ValueError()
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            400, "No se pudo validar el acceso con ORCID. Inténtalo de nuevo"
        ) from None
    try:
        with httpx.Client(timeout=20) as client:
            result = client.post(
                "https://sandbox.orcid.org/oauth/token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.orcid_client_id,
                    "client_secret": settings.orcid_client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.orcid_redirect_uri,
                },
            )
            result.raise_for_status()
            identity = result.json()
        orcid = identity["orcid"]
        if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", orcid):
            raise ValueError()
    except (httpx.HTTPError, KeyError, ValueError):
        raise HTTPException(502, "ORCID no pudo confirmar tu identidad") from None
    # Do not merge accounts by unverified email or infer email verification from ORCID.
    user = db.scalar(select(User).where(User.orcid_id == orcid))
    if not user:
        user = User(orcid_id=orcid, name=str(identity.get("name") or "Investigador ORCID")[:120])
        db.add(user)
        db.flush()
    audit(db, user, "orcid_login")
    db.commit()
    response = RedirectResponse(settings.app_base_url + "/mis-revisiones", status_code=303)
    response.delete_cookie("oauth_state", path="/")
    set_session(response, user)
    return response
