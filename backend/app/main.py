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
from app.routers import backup as backup_router
from app import scheduler_instance

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
    "ALTER TABLE teachers ADD COLUMN min_start_slot INTEGER",
    "ALTER TABLE teachers ADD COLUMN max_end_slot INTEGER",
    "ALTER TABLE teachers ADD COLUMN preferred_shift TEXT",
    "ALTER TABLE teachers ADD COLUMN max_consecutive_lessons INTEGER",
    "ALTER TABLE scheduling_rules ADD COLUMN no_student_gaps BOOLEAN DEFAULT 1",
    "ALTER TABLE scheduling_rules ADD COLUMN minimize_teacher_gaps BOOLEAN DEFAULT 1",
    "ALTER TABLE scheduling_rules ADD COLUMN teacher_gap_weight INTEGER DEFAULT 10",
    "ALTER TABLE scheduling_rules ADD COLUMN no_same_subject_twice_per_day BOOLEAN DEFAULT 1",
    "ALTER TABLE scheduling_rules ADD COLUMN distribute_subjects_weight INTEGER DEFAULT 5",
    "CREATE TABLE IF NOT EXISTS backup_config (id INTEGER PRIMARY KEY DEFAULT 1, enabled BOOLEAN DEFAULT 0, frequency TEXT DEFAULT 'weekly', onedrive_client_id TEXT, onedrive_refresh_token TEXT, folder_path TEXT DEFAULT 'GeradorHorarios/Backups', last_backup_at DATETIME, next_backup_at DATETIME)",
    "CREATE TABLE IF NOT EXISTS backup_history (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at DATETIME, status TEXT, destination TEXT DEFAULT 'download', size_bytes INTEGER, message TEXT, filename TEXT)",
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
app.include_router(backup_router.router, prefix=API_PREFIX, dependencies=[_auth])


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


@app.on_event("startup")
def seed_demo_data():
    from app.models.models import (
        Cluster, School, AcademicYear, TimeSlotConfig, Subject, Teacher,
        TeacherSubject, TeacherSchoolAssignment, Class, CurriculumEntry,
        SchedulingRules
    )
    import datetime as dt
    db = SessionLocal()
    try:
        # Demo user
        if not db.query(User).filter(User.username == "demo").first():
            db.add(User(
                username="demo", full_name="Utilizador Demo",
                hashed_password=hash_password("demo_nologin_" + str(__import__('os').urandom(8).hex())),
                role="viewer", is_active=True,
            ))
            db.commit()

        # Cluster
        cluster = db.query(Cluster).filter(Cluster.name == "Agrupamento Demo").first()
        if not cluster:
            cluster = Cluster(name="Agrupamento Demo", description="Dados de demonstração — não editáveis")
            db.add(cluster); db.flush()

            school = School(cluster_id=cluster.id, name="EB 2,3 Prof. António Neves", code="DEMO-EB23")
            db.add(school); db.flush()

            year = AcademicYear(cluster_id=cluster.id, name="2025/2026",
                start_date=dt.date(2025, 9, 15), end_date=dt.date(2026, 6, 20), is_active=True)
            db.add(year); db.flush()

            # Time slots (Mon-Fri, 7 slots + breaks)
            times = [
                (1, dt.time(8, 30),  dt.time(9, 20),  False),
                (2, dt.time(9, 20),  dt.time(10, 10), False),
                (0, dt.time(10, 10), dt.time(10, 25), True),   # break
                (3, dt.time(10, 25), dt.time(11, 15), False),
                (4, dt.time(11, 15), dt.time(12, 5),  False),
                (0, dt.time(12, 5),  dt.time(13, 30), True),   # lunch
                (5, dt.time(13, 30), dt.time(14, 20), False),
                (6, dt.time(14, 20), dt.time(15, 10), False),
                (0, dt.time(15, 10), dt.time(15, 25), True),   # break
                (7, dt.time(15, 25), dt.time(16, 15), False),
            ]
            for day in range(5):
                for slot_num, start, end, is_break in times:
                    if slot_num == 0:
                        continue  # skip breaks for time_slot_configs
                    db.add(TimeSlotConfig(
                        academic_year_id=year.id, school_id=school.id,
                        day_of_week=day, slot_number=slot_num,
                        start_time=start, end_time=end, is_break=False
                    ))

            # Subjects
            subj_data = [
                ("Português", "#e74c3c"), ("Matemática", "#3498db"), ("Inglês", "#2ecc71"),
                ("Ciências Naturais", "#27ae60"), ("História", "#8e44ad"),
                ("Geografia", "#f39c12"), ("Educação Física", "#e67e22"),
                ("Arte", "#1abc9c"), ("TIC", "#95a5a6"), ("Ed. Moral e Religião", "#d35400"),
            ]
            subjects = {}
            for sname, scolor in subj_data:
                s = Subject(cluster_id=cluster.id, name=sname, color=scolor)
                db.add(s); db.flush()
                subjects[sname] = s

            # Teachers
            teacher_subj = {
                "Maria Costa": ["Português", "História"],
                "João Silva": ["Matemática"],
                "Ana Ferreira": ["Inglês", "TIC"],
                "Pedro Santos": ["Ciências Naturais", "Geografia"],
                "Sofia Rodrigues": ["Educação Física", "Arte"],
                "Carlos Oliveira": ["Ed. Moral e Religião", "História"],
            }
            teachers_map = {}
            for tname, snames in teacher_subj.items():
                t = Teacher(cluster_id=cluster.id, name=tname, max_daily_lessons=5)
                db.add(t); db.flush()
                teachers_map[tname] = t
                for sn in snames:
                    if sn in subjects:
                        db.add(TeacherSubject(teacher_id=t.id, subject_id=subjects[sn].id))
                db.add(TeacherSchoolAssignment(
                    teacher_id=t.id, school_id=school.id,
                    academic_year_id=year.id, travel_time_minutes=0
                ))

            # Classes
            class_data = [
                ("5A", 5, 26), ("5B", 5, 24), ("6A", 6, 25), ("6B", 6, 22),
                ("7A", 7, 23), ("8A", 8, 24), ("9A", 9, 22),
            ]
            classes_list = []
            for cname, ylevel, nstud in class_data:
                c = Class(
                    school_id=school.id, academic_year_id=year.id,
                    name=cname, year_level=ylevel, num_students=nstud
                )
                db.add(c); db.flush()
                classes_list.append(c)

            # Curriculum (5th/6th grade Portuguese curriculum)
            curriculum_5 = [
                ("Português", 5, 2), ("Matemática", 5, 2), ("Inglês", 3, 1),
                ("Ciências Naturais", 2, 1), ("História", 2, 1), ("Geografia", 2, 1),
                ("Educação Física", 2, 1), ("Arte", 2, 1), ("Ed. Moral e Religião", 1, 1),
            ]
            curriculum_7 = [
                ("Português", 4, 2), ("Matemática", 4, 2), ("Inglês", 3, 1),
                ("Ciências Naturais", 3, 1), ("História", 3, 1), ("Geografia", 2, 1),
                ("Educação Física", 2, 1), ("TIC", 2, 1),
            ]
            for cls in classes_list:
                curric = curriculum_5 if cls.year_level <= 6 else curriculum_7
                for sname, hpw, split_count in curric:
                    if sname in subjects:
                        db.add(CurriculumEntry(
                            class_id=cls.id, subject_id=subjects[sname].id,
                            hours_per_week=float(hpw), is_split=split_count > 1,
                            split_count=split_count, consecutive_pairs=0,
                        ))

            # Scheduling rules
            db.add(SchedulingRules(
                cluster_id=cluster.id, academic_year_id=year.id,
                max_periods_per_day_class=5, max_periods_per_day_teacher=6,
                max_consecutive_periods_class=2, max_consecutive_periods_teacher=4,
                avoid_isolated_teacher=True, no_student_gaps=True,
                minimize_teacher_gaps=True, teacher_gap_weight=10,
                no_same_subject_twice_per_day=True, distribute_subjects_weight=5,
            ))

            db.commit()
            logger.info("Dados de demonstração criados com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao criar dados demo: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def start_scheduler():
    scheduler_instance.start_scheduler()
    # Load saved backup config and reschedule
    db = SessionLocal()
    try:
        from app.models.models import BackupConfig
        cfg = db.query(BackupConfig).filter(BackupConfig.id == 1).first()
        if cfg and cfg.enabled and cfg.frequency != "manual":
            scheduler_instance.reschedule_backup(cfg.frequency)
    except Exception:
        pass
    finally:
        db.close()


@app.on_event("shutdown")
def stop_scheduler():
    scheduler_instance.stop_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}
