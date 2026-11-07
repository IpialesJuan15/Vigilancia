import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def now():
    return datetime.now(UTC)


class Timestamps:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class User(Timestamps, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role in ('admin','curator','subscriber')"),)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(512))
    name: Mapped[str] = mapped_column(String(120))
    orcid_id: Mapped[str | None] = mapped_column(String(19), unique=True)
    institution: Mapped[str | None] = mapped_column(String(250))
    role: Mapped[str] = mapped_column(String(20), default="subscriber")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_prefs: Mapped[dict] = mapped_column(JSON, default=dict)
    session_version: Mapped[int] = mapped_column(Integer, default=0)


class AuthToken(Timestamps, Base):
    __tablename__ = "auth_tokens"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    digest: Mapped[str] = mapped_column(String(64), unique=True)
    purpose: Mapped[str] = mapped_column(String(20))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Timestamps, Base):
    __tablename__ = "audit_log"
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    entity: Mapped[str] = mapped_column(String(100), default="user")
    entity_id: Mapped[str | None] = mapped_column(String(36))
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)


class LivingReview(Timestamps, Base):
    __tablename__ = "living_reviews"
    original_doi: Mapped[str] = mapped_column(String(255), unique=True)
    original_title: Mapped[str] = mapped_column(Text, default="Revisión en preparación")
    normalized_title: Mapped[str | None] = mapped_column(Text, index=True, unique=True)
    original_authors: Mapped[list] = mapped_column(JSON, default=list)
    journal: Mapped[str | None] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(Integer)
    license: Mapped[str | None] = mapped_column(String(100))
    oa_url: Mapped[str | None] = mapped_column(Text)
    owner_curator_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str] = mapped_column(Text, default="Esperando la lectura del documento")
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    source_key: Mapped[str | None] = mapped_column(Text)
    source_sha256: Mapped[str | None] = mapped_column(String(64))
    source_format: Mapped[str | None] = mapped_column(String(10))
    uploaded_key: Mapped[str | None] = mapped_column(Text)
    document: Mapped[dict | None] = mapped_column(JSON)
    license_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
