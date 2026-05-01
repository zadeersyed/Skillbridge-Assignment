"""
Pytest configuration.

Two test modes:
  1. Tests marked with `@pytest.mark.db` hit the REAL test database
     (reads DATABASE_URL from .env).
  2. Other tests use an in-memory SQLite database for speed.

At least two tests use the real DB as required by the assignment.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dotenv import load_dotenv
load_dotenv()

from src.db.database import Base, get_db
import src.models  # noqa
from src.main import app

# ── In-memory SQLite engine for fast unit tests ────────────────────────────────
SQLITE_URL = "sqlite:///./test_temp.db"
sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
SQLiteSession = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)


def override_get_db_sqlite():
    db = SQLiteSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client():
    """Test client with in-memory SQLite DB — fast, isolated per test."""
    Base.metadata.create_all(bind=sqlite_engine)
    app.dependency_overrides[get_db] = override_get_db_sqlite
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=sqlite_engine)


# ── Real PostgreSQL DB fixtures (for db-level tests) ──────────────────────────
real_db_url = os.getenv("DATABASE_URL", "")

real_engine = create_engine(real_db_url, pool_pre_ping=True) if real_db_url else None
RealSession = sessionmaker(autocommit=False, autoflush=False, bind=real_engine) if real_engine else None


def override_get_db_real():
    db = RealSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def real_client():
    """Test client backed by the real Neon PostgreSQL database."""
    if not real_engine:
        pytest.skip("DATABASE_URL not set — skipping real DB test")
    Base.metadata.create_all(bind=real_engine)
    app.dependency_overrides[get_db] = override_get_db_real
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
