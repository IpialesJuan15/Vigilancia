import os

os.environ.setdefault("JWT_SECRET", "test-only-key-with-more-than-32-characters")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def mail(monkeypatch):
    messages = []
    monkeypatch.setattr("app.services.auth.send_email.delay", lambda *args: messages.append(args))
    return messages


@pytest.fixture
def client(db, monkeypatch, mail):
    app.dependency_overrides[get_db] = lambda: db
    monkeypatch.setattr(
        "app.security.Redis",
        type(
            "RedisStub",
            (),
            {"from_url": staticmethod(lambda url: type("Counter", (), {"eval": lambda *a: 1})())},
        ),
    )
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def post(client, path, data):
    token = client.get("/auth/csrf").json()["token"]
    return client.post(
        path, json=data, headers={"Origin": "http://localhost:3000", "X-CSRF-Token": token}
    )


def register_verified(client, mail):
    post(
        client,
        "/auth/register",
        {"email": "user@example.org", "name": "Investigadora", "password": "a-secure-password-123"},
    )
    token = mail[-1][2].split("?token=")[1].split()[0]
    post(client, "/auth/verify-email", {"token": token})
    return token
