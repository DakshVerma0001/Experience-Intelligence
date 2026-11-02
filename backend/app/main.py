from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import audit, auth, health, imports, projects, review, search, settings as settings_routes
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.database import SessionLocal, init_db
from app.db.models.user import ROLE_ADMIN, User
from app.services.workflow.workflow_service import recover_interrupted_batches

logger = get_logger(__name__)


def _recover_interrupted_batches() -> None:
    db = SessionLocal()
    try:
        recovered = recover_interrupted_batches(db)
        if recovered:
            logger.warning(
                "Startup recovery: %s import batch(es) were still PROCESSING when the application last "
                "stopped and have been marked as failed/cancelled. Affected projects can be retried "
                "individually from the Review screen.",
                recovered,
            )
    finally:
        db.close()


def _seed_default_admin() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                email="admin@experience-intelligence.example",
                full_name="Default Admin",
                hashed_password=hash_password("ChangeMe123!"),
                role=ROLE_ADMIN,
            )
            db.add(admin)
            db.commit()
            logger.info(
                "Seeded default admin user: admin@experience-intelligence.example / ChangeMe123! "
                "(CHANGE THIS PASSWORD IMMEDIATELY)"
            )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    _seed_default_admin()
    _recover_interrupted_batches()
    yield


app = FastAPI(title="Experience Intelligence", version="1.0.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(imports.router)
app.include_router(review.router)
app.include_router(projects.router)
app.include_router(search.router)
app.include_router(settings_routes.router)
app.include_router(audit.router)


@app.get("/")
def root():
    return {"application": "Experience Intelligence", "status": "running", "docs": "/docs"}
