import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditLog, AuthToken, User
from app.security import digest
from app.tasks.mail import send_email


def audit(db: Session, user: User, action: str, before=None, after=None):
    db.add(AuditLog(actor_id=user.id, entity_id=user.id, action=action, before=before, after=after))


def issue_token(db: Session, user: User, purpose: str):
    token = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            user_id=user.id,
            digest=digest(token),
            purpose=purpose,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    db.commit()
    path = "verificar-correo" if purpose == "verify" else "restablecer"
    subject = "Verifica tu correo" if purpose == "verify" else "Restablece tu contraseña"
    url = f"{get_settings().app_base_url}/{path}?token={quote(token)}"
    send_email.delay(
        user.email,
        f"LiveSRL — {subject}",
        f"{subject} en LiveSRL:\n{url}\nEl enlace caduca en una hora. "
        "Si no solicitaste este mensaje, ignóralo.",
    )


def consume_token(db: Session, token: str, purpose: str) -> User:
    # Atomic consumption prevents two concurrent requests from reusing the token.
    user_id = db.execute(
        update(AuthToken)
        .where(
            AuthToken.digest == digest(token),
            AuthToken.purpose == purpose,
            AuthToken.used.is_(False),
            AuthToken.expires_at > datetime.now(UTC),
        )
        .values(used=True)
        .returning(AuthToken.user_id)
    ).scalar_one_or_none()
    if not user_id:
        raise HTTPException(400, "El enlace no es válido o ha caducado")
    return db.execute(select(User).where(User.id == user_id)).scalar_one()
