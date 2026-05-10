import os

os.environ["TESTING"] = "true"  # Must be set before app modules are imported

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app

_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(_engine)
_Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def clean_tables():
    """Truncate all rows between tests while keeping the schema."""
    yield
    session = _Session()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()


@pytest.fixture
def db():
    session = _Session()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "admin@test.fr",
            "password": "TestPass2026!",
            "full_name": "Admin Test",
            "role": "admin",
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def be_token(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "be@test.fr",
            "password": "TestPass2026!",
            "full_name": "Bureau Etudes",
            "role": "BE",
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def be_headers(be_token):
    return {"Authorization": f"Bearer {be_token}"}
