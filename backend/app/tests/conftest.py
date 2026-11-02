import atexit
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP_STORAGE = tempfile.mkdtemp()
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MOCK_PORTAL_PORT = 9091

os.environ["APP_DATABASE_URL"] = f"sqlite:///{_TMP_DB.name}"
os.environ["APP_STORAGE_DIR"] = _TMP_STORAGE
os.environ["VECTOR_STORE_DIR"] = os.path.join(_TMP_STORAGE, "chroma")
os.environ["APP_SECRET_KEY"] = "test-secret"
os.environ["PORTAL_IMPORT_URL"] = f"http://127.0.0.1:{_MOCK_PORTAL_PORT}/api/internal/experience-import"
os.environ["PORTAL_HEALTH_URL"] = f"http://127.0.0.1:{_MOCK_PORTAL_PORT}/api/internal/health"
os.environ["PORTAL_IMPORT_CLIENT_ID"] = "experience-intelligence"
os.environ["PORTAL_IMPORT_SECRET"] = "dev-shared-secret-change-me"


def _start_mock_portal() -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "mock_portal.main:app", "--host", "127.0.0.1", "--port", str(_MOCK_PORTAL_PORT)],
        cwd=str(_REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    health_url = os.environ["PORTAL_HEALTH_URL"]
    for _ in range(60):
        try:
            urllib.request.urlopen(health_url, timeout=1)
            return proc
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Mock portal failed to start for tests")


_mock_portal_proc = _start_mock_portal()
atexit.register(_mock_portal_proc.terminate)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.db.database import SessionLocal, init_db  # noqa: E402
from app.db.models.user import ROLE_ADMIN, ROLE_CONTRIBUTOR, ROLE_REVIEWER, User  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    init_db()
    db = SessionLocal()
    for email, role in [
        ("admin@test.example", ROLE_ADMIN),
        ("reviewer@test.example", ROLE_REVIEWER),
        ("contributor@test.example", ROLE_CONTRIBUTOR),
    ]:
        if not db.query(User).filter(User.email == email).first():
            db.add(User(email=email, full_name=role.title(), hashed_password=hash_password("Password123!"), role=role))
    db.commit()
    db.close()
    yield


@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _token_for(role: str) -> str:
    db = SessionLocal()
    user = db.query(User).filter(User.role == role).first()
    db.close()
    return create_access_token(user.id, user.role)


@pytest.fixture
def admin_headers():
    return {"Authorization": f"Bearer {_token_for(ROLE_ADMIN)}"}


@pytest.fixture
def reviewer_headers():
    return {"Authorization": f"Bearer {_token_for(ROLE_REVIEWER)}"}


@pytest.fixture
def contributor_headers():
    return {"Authorization": f"Bearer {_token_for(ROLE_CONTRIBUTOR)}"}
