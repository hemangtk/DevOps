"""Test fixtures. Uses a SQLite file DB, never the production Postgres.
Name: Hemang | Enrollment number: 24bcs10209
"""
import os
import tempfile

import pytest

# MUST be set before app modules import the config
_tmpdir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["APP_VERSION"] = "test"
os.environ["ENVIRONMENT"] = "test"

from fastapi.testclient import TestClient            # noqa: E402

from app import db as database                        # noqa: E402
from app.main import app                              # noqa: E402
from app.models import Base                           # noqa: E402


@pytest.fixture(autouse=True)
def fresh_schema():
    """A clean schema per test - isolated, and nowhere near production data."""
    Base.metadata.drop_all(bind=database.engine)
    Base.metadata.create_all(bind=database.engine)
    yield
    Base.metadata.drop_all(bind=database.engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
