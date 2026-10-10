"""Test setup: a real PostgreSQL database, migrated with Alembic.

Uses TEST_DATABASE_URL (default: local patient_registration_test). Tables are
truncated between tests.
"""

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://localhost/patient_registration_test"
)
os.environ["API_KEY"] = "test-api-key"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["VAPI_WEBHOOK_SECRET"] = "test-vapi-secret"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE call_sessions, patients RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"Authorization": "Bearer test-api-key"})
        yield c


@pytest.fixture
def anon_client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def valid_patient():
    return {
        "first_name": "Jane",
        "last_name": "Doe",
        "date_of_birth": "04/12/1988",
        "sex": "Female",
        "phone_number": "(512) 555-0142",
        "address_line_1": "100 Congress Ave",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
    }
