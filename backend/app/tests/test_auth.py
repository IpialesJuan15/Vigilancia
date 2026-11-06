from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models import AuditLog, AuthToken, User
from app.security import digest
from app.tests.conftest import post, register_verified

CREDS = {"email": "user@example.org", "password": "a-secure-password-123"}


def test_complete_registration_verification_login_logout(client, mail, db):
    assert client.get("/me").status_code == 401
    assert post(client, "/auth/register", {**CREDS, "name": "Investigadora"}).status_code == 202
    user = db.scalar(select(User))
    assert user.role == "subscriber"
    assert user.password_hash.startswith("$argon2id$")
    assert CREDS["password"] not in user.password_hash
    assert post(client, "/auth/login", CREDS).status_code == 403
    token = mail[0][2].split("?token=")[1].split()[0]
    assert db.scalar(select(AuthToken)).digest == digest(token)
    assert post(client, "/auth/verify-email", {"token": token}).status_code == 200
    assert post(client, "/auth/verify-email", {"token": token}).status_code == 400
    response = post(client, "/auth/login", CREDS)
    assert response.status_code == 200
    assert "password_hash" not in response.json()
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    old_session = client.cookies["session"]
    assert client.get("/me").json()["email_verified"] is True
    assert client.get("/reviews").json()["items"] == []
    assert post(client, "/auth/logout", {}).status_code == 200
    client.cookies.set("session", old_session)
    assert client.get("/me").status_code == 401
    assert len(db.scalars(select(AuditLog)).all()) == 4


@pytest.mark.parametrize(
    "data",
    [
        {**CREDS, "name": "Investigadora", "role": "admin"},
        {**CREDS, "name": "  "},
        {**CREDS, "name": "Yo", "password": "short"},
        {**CREDS, "name": "Yo", "email": "invalid"},
    ],
)
def test_invalid_registration_does_not_create_account(client, db, data):
    response = post(client, "/auth/register", data)
    assert response.status_code == 422
    assert not db.scalar(select(User))
    assert CREDS["password"] not in response.text


def test_csrf_and_origin_required(client):
    assert client.post("/auth/login", json=CREDS).status_code == 403
    token = client.get("/auth/csrf").json()["token"]
    assert (
        client.post(
            "/auth/login",
            json=CREDS,
            headers={"Origin": "https://evil.example", "X-CSRF-Token": token},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/auth/login",
            json=CREDS,
            headers={"Origin": "http://localhost:3000", "X-CSRF-Token": "wrong"},
        ).status_code
        == 403
    )


def test_wrong_password_and_unknown_account(client, mail):
    register_verified(client, mail)
    a = post(client, "/auth/login", {**CREDS, "password": "wrong"})
    b = post(client, "/auth/login", {**CREDS, "email": "unknown@example.org"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_duplicate_register_normalized_email(client, mail, db):
    register_verified(client, mail)
    response = post(client, "/auth/register", {**CREDS, "email": "USER@example.org", "name": "Yo"})
    assert response.status_code == 202
    assert len(db.scalars(select(User)).all()) == 1


def test_reset_single_use_and_session_invalidation(client, mail):
    register_verified(client, mail)
    post(client, "/auth/login", CREDS)
    session = client.cookies["session"]
    assert post(client, "/auth/password/forgot", {"email": CREDS["email"]}).status_code == 202
    token = mail[-1][2].split("?token=")[1].split()[0]
    data = {"token": token, "password": "replacement-password-123"}
    assert post(client, "/auth/password/reset", data).status_code == 200
    client.cookies.set("session", session)
    assert client.get("/me").status_code == 401
    assert post(client, "/auth/password/reset", data).status_code == 400
    assert post(client, "/auth/login", CREDS).status_code == 401
    assert post(client, "/auth/login", {**CREDS, "password": data["password"]}).status_code == 200


def test_expired_and_wrong_purpose_tokens(client, mail, db):
    token = register_verified(client, mail)
    assert (
        post(
            client, "/auth/password/reset", {"token": token, "password": "long-password-123"}
        ).status_code
        == 400
    )
    db.add(
        AuthToken(
            user_id=db.scalar(select(User)).id,
            digest=digest("x" * 32),
            purpose="reset",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    db.commit()
    assert (
        post(
            client, "/auth/password/reset", {"token": "x" * 32, "password": "long-password-123"}
        ).status_code
        == 400
    )


def test_resend_and_forgot_do_not_enumerate(client, mail):
    post(client, "/auth/register", {**CREDS, "name": "Investigadora"})
    a = post(client, "/auth/verification/resend", {"email": CREDS["email"]})
    b = post(client, "/auth/verification/resend", {"email": "unknown@example.org"})
    assert a.json() == b.json()
    assert len(mail) == 2
    before = len(mail)
    post(client, "/auth/password/forgot", {"email": CREDS["email"]})
    assert len(mail) == before


@pytest.mark.parametrize(
    "payload",
    [
        {"sub": "missing", "ver": 0, "kind": "session", "exp": 1},
        {"sub": "missing", "ver": 0, "kind": "session", "exp": 9999999999},
        {"sub": "missing"},
    ],
)
def test_expired_or_invalid_sessions(client, payload):
    token = jwt.encode(payload, get_settings().jwt_secret, algorithm="HS256")
    client.cookies.set("session", token)
    assert client.get("/me").status_code == 401


def test_rbac_and_audited_role_change(client, mail, db):
    register_verified(client, mail)
    post(client, "/auth/login", CREDS)
    assert client.get("/admin/users").status_code == 403
    admin = db.scalar(select(User))
    admin.role = "admin"
    other = User(name="Curadora", email="curator@example.org", email_verified=True)
    db.add(other)
    db.commit()
    assert client.get("/admin/users").status_code == 200
    csrf = client.get("/auth/csrf").json()["token"]
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": csrf}
    response = client.patch(
        f"/admin/users/{other.id}/role", json={"role": "curator"}, headers=headers
    )
    assert response.json()["role"] == "curator"
    assert db.get(User, other.id).session_version == 1
    assert (
        client.patch(
            f"/admin/users/{admin.id}/role", json={"role": "subscriber"}, headers=headers
        ).status_code
        == 409
    )
    assert (
        client.patch(
            "/admin/users/missing/role", json={"role": "admin"}, headers=headers
        ).status_code
        == 404
    )
    assert db.scalar(select(AuditLog).where(AuditLog.action == "role_changed"))


def test_rate_limit_and_redis_failure(client, monkeypatch):
    from redis.exceptions import ConnectionError

    class Counter:
        def eval(self, *a):
            return 11

    monkeypatch.setattr("app.security.Redis.from_url", lambda url: Counter())
    assert post(client, "/auth/login", CREDS).status_code == 429

    def fail(*args):
        raise ConnectionError()

    monkeypatch.setattr("app.security.Redis.from_url", fail)
    assert post(client, "/auth/login", CREDS).status_code == 503


def test_health_dependencies_and_headers(client, monkeypatch):
    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, *args):
            pass

    monkeypatch.setattr("app.main.engine.connect", lambda: Connection())
    monkeypatch.setattr(
        "app.main.Redis.from_url", lambda url: type("R", (), {"ping": lambda self: True})()
    )
    response = client.get("/health")
    assert response.json()["status"] == "ok"
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    def fail():
        raise RuntimeError()

    monkeypatch.setattr("app.main.engine.connect", fail)
    assert client.get("/health").status_code == 503
    assert client.get("/does-not-exist").json()["code"] == "http_404"


def test_empty_catalog(client):
    assert client.get("/public/reviews").json() == {"items": [], "total": 0, "page": 1}
