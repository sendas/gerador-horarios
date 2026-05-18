import os
import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, SessionLocal, Base
from app.models import models as _models  # noqa
from app.models.user import User
from app.auth import hash_password, get_current_user
from app.routers import (
    clusters, schools, academic_years, time_slots, rooms,
    subjects, classes, subject_groups, teachers, non_teaching,
    timetables, exports
)
from app.routers import imports as imports_router
from app.routers.auth import router as auth_router
from app.routers import scheduling_rules as scheduling_rules_router

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

# Add new columns to existing tables (SQLite does not support IF NOT EXISTS in ALTER TABLE)
from sqlalchemy import text  # noqa: E402
for _sql in [
    "ALTER TABLE curriculum_entries ADD COLUMN consecutive_pairs INTEGER DEFAULT 0",
    "ALTER TABLE curriculum_entries ADD COLUMN is_semestral BOOLEAN DEFAULT 0",
    "ALTER TABLE curriculum_entries ADD COLUMN semester INTEGER",
    "ALTER TABLE curriculum_entries ADD COLUMN paired_entry_id INTEGER REFERENCES curriculum_entries(id)",
    "ALTER TABLE scheduled_lessons ADD COLUMN semester INTEGER",
]:
    try:
        with engine.connect() as _conn:
            _conn.execute(text(_sql))
            _conn.commit()
    except Exception:
        pass  # column already exists

app = FastAPI(
    title="Gerador de Horários API",
    description="API para geração automática de horários escolares",
    version="1.0.0",
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

# Auth router — público (login não requer token)
app.include_router(auth_router, prefix=API_PREFIX)

# Routers protegidos — requerem token válido
_auth = Depends(get_current_user)

app.include_router(clusters.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(schools.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(academic_years.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(time_slots.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(rooms.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(subjects.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(classes.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(subject_groups.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(teachers.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(non_teaching.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(timetables.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(exports.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(imports_router.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(scheduling_rules_router.router, prefix=API_PREFIX, dependencies=[_auth])


@app.on_event("startup")
def create_default_admin():
    db = SessionLocal()
    try:
        if not db.query(User).first():
            default_password = os.getenv("ADMIN_PASSWORD", "admin123")
            admin = User(
                username="admin",
                hashed_password=hash_password(default_password),
                full_name="Administrador",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Utilizador admin criado com password padrão. Muda-a após o primeiro login!")
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}
