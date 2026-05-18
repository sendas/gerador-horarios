from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import models as _models  # noqa: ensure models are registered
from app.database import Base
from app.routers import (
    clusters, schools, academic_years, time_slots, rooms,
    subjects, classes, subject_groups, teachers, non_teaching,
    timetables, exports
)

Base.metadata.create_all(bind=engine)

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

app.include_router(clusters.router, prefix=API_PREFIX)
app.include_router(schools.router, prefix=API_PREFIX)
app.include_router(academic_years.router, prefix=API_PREFIX)
app.include_router(time_slots.router, prefix=API_PREFIX)
app.include_router(rooms.router, prefix=API_PREFIX)
app.include_router(subjects.router, prefix=API_PREFIX)
app.include_router(classes.router, prefix=API_PREFIX)
app.include_router(subject_groups.router, prefix=API_PREFIX)
app.include_router(teachers.router, prefix=API_PREFIX)
app.include_router(non_teaching.router, prefix=API_PREFIX)
app.include_router(timetables.router, prefix=API_PREFIX)
app.include_router(exports.router, prefix=API_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok"}
