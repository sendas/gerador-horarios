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
from app.routers import service_distribution as service_distribution_router
from app.routers import timetable_locks as timetable_locks_router
from app.routers import settings as settings_router
from app.routers import ai_chat as ai_chat_router
from app.routers import curriculum_plans as curriculum_plans_router
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
    "ALTER TABLE subjects ADD COLUMN weekly_structure TEXT DEFAULT '1+1'",
    "ALTER TABLE subjects ADD COLUMN regime TEXT DEFAULT 'annual'",
    "ALTER TABLE subjects ADD COLUMN default_semester INTEGER",
    "ALTER TABLE subjects ADD COLUMN is_physical_education BOOLEAN DEFAULT 0",
    "ALTER TABLE subjects ADD COLUMN can_exempt_articulado BOOLEAN DEFAULT 0",
    "ALTER TABLE scheduling_rules ADD COLUMN students_start_slot_1 BOOLEAN DEFAULT 1",
    "ALTER TABLE scheduling_rules ADD COLUMN no_pe_after_lunch BOOLEAN DEFAULT 1",
    "ALTER TABLE scheduling_rules ADD COLUMN lunch_after_slot INTEGER DEFAULT 4",
    "ALTER TABLE teachers ADD COLUMN teaching_component INTEGER",
    "ALTER TABLE timetables ADD COLUMN generation_log TEXT",
    "ALTER TABLE classes ADD COLUMN notes TEXT",
    "ALTER TABLE curriculum_entries ADD COLUMN teacher_id INTEGER REFERENCES teachers(id)",
    "CREATE TABLE IF NOT EXISTS timetable_locks (id INTEGER PRIMARY KEY AUTOINCREMENT, timetable_id INTEGER NOT NULL REFERENCES timetables(id), lock_type TEXT NOT NULL, entity_id INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS backup_config (id INTEGER PRIMARY KEY DEFAULT 1, enabled BOOLEAN DEFAULT 0, frequency TEXT DEFAULT 'weekly', onedrive_client_id TEXT, onedrive_refresh_token TEXT, folder_path TEXT DEFAULT 'GeradorHorarios/Backups', last_backup_at DATETIME, next_backup_at DATETIME)",
    "CREATE TABLE IF NOT EXISTS backup_history (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at DATETIME, status TEXT, destination TEXT DEFAULT 'download', size_bytes INTEGER, message TEXT, filename TEXT)",
    "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)",
    "ALTER TABLE teachers ADD COLUMN credit_hours INTEGER DEFAULT 0",
    "ALTER TABLE teachers ADD COLUMN birth_date DATE",
    "CREATE TABLE IF NOT EXISTS curriculum_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, cluster_id INTEGER NOT NULL REFERENCES clusters(id), academic_year_id INTEGER NOT NULL REFERENCES academic_years(id), year_level INTEGER NOT NULL, subject_id INTEGER NOT NULL REFERENCES subjects(id), hours_per_week REAL NOT NULL DEFAULT 2.0, weekly_structure TEXT DEFAULT '1+1')",
    "ALTER TABLE subjects ADD COLUMN paired_subject_id INTEGER REFERENCES subjects(id)",
    "ALTER TABLE teacher_school_assignments ADD COLUMN is_primary BOOLEAN DEFAULT 0",
    "ALTER TABLE curriculum_plans ADD COLUMN is_semestral BOOLEAN DEFAULT 0",
    "ALTER TABLE curriculum_plans ADD COLUMN semester INTEGER",
    "ALTER TABLE curriculum_plans ADD COLUMN paired_subject_id INTEGER REFERENCES subjects(id)",
    "ALTER TABLE teachers ADD COLUMN total_hours INTEGER DEFAULT 25",
    "ALTER TABLE teachers ADD COLUMN base_teaching_hours INTEGER DEFAULT 22",
    "ALTER TABLE teachers ADD COLUMN credit_role TEXT",
    "ALTER TABLE teachers ADD COLUMN te_hours INTEGER DEFAULT 3",
    "ALTER TABLE teachers ADD COLUMN te_role TEXT",
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
app.include_router(service_distribution_router.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(timetable_locks_router.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(settings_router.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(ai_chat_router.router, prefix=API_PREFIX, dependencies=[_auth])
app.include_router(curriculum_plans_router.router, prefix=API_PREFIX, dependencies=[_auth])


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


def _build_demo_timetable(db, timetable_id, classes_list, teacher_by_subject_id):
    """Greedy schedule — alunos sempre no 1º tempo, EF nunca depois do almoço."""
    from app.models.models import ScheduledLesson, CurriculumEntry, Subject

    class_slots: dict = {}
    teacher_slots: dict = {}
    DAYS, MAX_SLOT, LUNCH_AFTER = 5, 7, 4

    def find_slot(class_id, teacher_id, start_day=0, max_slot=MAX_SLOT, only_slots=None):
        for day in range(start_day, DAYS + start_day):
            d = day % DAYS
            # First slot of day must be 1 if day not yet started for this class
            day_used = any(d2 == d for (d2, _) in class_slots.get(class_id, set()))
            slot_range = only_slots if only_slots else range(1, max_slot + 1)
            for slot in slot_range:
                if not day_used and slot != 1:
                    continue  # first lesson of day must be slot 1
                if (d, slot) in class_slots.get(class_id, set()):
                    continue
                if teacher_id and (d, slot) in teacher_slots.get(teacher_id, set()):
                    continue
                return d, slot
        return None, None

    def find_consecutive_pair(class_id, teacher_id, start_day=0, max_slot=MAX_SLOT):
        for day in range(start_day, DAYS + start_day):
            d = day % DAYS
            day_used = any(d2 == d for (d2, _) in class_slots.get(class_id, set()))
            for slot in range(1, max_slot):
                if not day_used and slot != 1:
                    continue
                occupied_class = class_slots.get(class_id, set())
                occupied_teacher = teacher_slots.get(teacher_id, set()) if teacher_id else set()
                if (d, slot) not in occupied_class and (d, slot + 1) not in occupied_class:
                    if (d, slot) not in occupied_teacher and (d, slot + 1) not in occupied_teacher:
                        return d, slot
        return None, None

    def place(class_id, entry_id, teacher_id, day, slot):
        class_slots.setdefault(class_id, set()).add((day, slot))
        if teacher_id:
            teacher_slots.setdefault(teacher_id, set()).add((day, slot))
        db.add(ScheduledLesson(
            timetable_id=timetable_id, curriculum_entry_id=entry_id,
            day_of_week=day, slot_number=slot, teacher_id=teacher_id,
        ))

    for cls_idx, cls in enumerate(classes_list):
        start_day = cls_idx % DAYS
        entries = db.query(CurriculumEntry).filter(CurriculumEntry.class_id == cls.id).all()
        for entry in entries:
            n = entry.split_count if entry.is_split else max(1, round(entry.hours_per_week))
            teacher_id = teacher_by_subject_id.get(entry.subject_id)
            pairs = getattr(entry, 'consecutive_pairs', 0) or 0
            is_pe = entry.subject and getattr(entry.subject, 'is_physical_education', False)
            pe_max_slot = LUNCH_AFTER if is_pe else MAX_SLOT
            placed = 0
            for _ in range(pairs):
                if placed + 2 > n:
                    break
                d, s = find_consecutive_pair(cls.id, teacher_id, start_day, pe_max_slot)
                if d is not None:
                    place(cls.id, entry.id, teacher_id, d, s)
                    place(cls.id, entry.id, teacher_id, d, s + 1)
                    placed += 2
            while placed < n:
                d, s = find_slot(cls.id, teacher_id, start_day, pe_max_slot)
                if d is None:
                    break
                place(cls.id, entry.id, teacher_id, d, s)
                placed += 1


@app.on_event("startup")
def seed_demo_data():
    from app.models.models import (
        Cluster, School, AcademicYear, TimeSlotConfig, Subject, Teacher,
        TeacherSubject, TeacherSchoolAssignment, Class, CurriculumEntry,
        SchedulingRules, Timetable, ScheduledLesson,
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

        # Cluster — only seed once
        cluster = db.query(Cluster).filter(Cluster.name == "Agrupamento Demo").first()
        if not cluster:
            cluster = Cluster(name="Agrupamento Demo", description="Dados de demonstração")
            db.add(cluster); db.flush()

            school = School(cluster_id=cluster.id, name="EB 2,3 Prof. António Neves", code="DEMO-EB23")
            db.add(school); db.flush()

            year = AcademicYear(cluster_id=cluster.id, name="2025/2026",
                start_date=dt.date(2025, 9, 15), end_date=dt.date(2026, 6, 20), is_active=True)
            db.add(year); db.flush()

            # Time slots Mon–Fri, 7 slots
            slot_times = [
                (1, dt.time(8, 30),  dt.time(9, 20)),
                (2, dt.time(9, 20),  dt.time(10, 10)),
                (3, dt.time(10, 25), dt.time(11, 15)),
                (4, dt.time(11, 15), dt.time(12, 5)),
                (5, dt.time(13, 30), dt.time(14, 20)),
                (6, dt.time(14, 20), dt.time(15, 10)),
                (7, dt.time(15, 25), dt.time(16, 15)),
            ]
            for day in range(5):
                for snum, start, end in slot_times:
                    db.add(TimeSlotConfig(
                        academic_year_id=year.id, school_id=school.id,
                        day_of_week=day, slot_number=snum,
                        start_time=start, end_time=end, is_break=False,
                    ))

            # Subjects with weekly_structure
            # (name, color, weekly_structure, regime)
            subj_data = [
                ("Português",           "#e74c3c", "2+1",   "annual"),
                ("Matemática",          "#3498db", "2+1",   "annual"),
                ("Inglês",              "#2ecc71", "1+1+1", "annual"),
                ("Ciências Naturais",   "#27ae60", "1+1",   "annual"),
                ("História",            "#8e44ad", "1+1",   "annual"),
                ("Geografia",           "#f39c12", "1+1",   "annual"),
                ("Educação Física",     "#e67e22", "1+1",   "annual"),
                ("Arte",                "#1abc9c", "1+1",   "annual"),
                ("TIC",                 "#95a5a6", "1+1",   "annual"),
                ("Ed. Moral e Religião","#d35400", "1",     "annual"),
            ]
            subjects = {}
            for sname, scolor, wstruct, regime in subj_data:
                s = Subject(
                    cluster_id=cluster.id, name=sname, color=scolor,
                    weekly_structure=wstruct, regime=regime,
                    is_physical_education=(sname == "Educação Física"),
                )
                db.add(s); db.flush()
                subjects[sname] = s

            # Teachers
            teacher_subj_map = {
                "Maria Costa":    ["Português", "História"],
                "João Silva":     ["Matemática"],
                "Ana Ferreira":   ["Inglês", "TIC"],
                "Pedro Santos":   ["Ciências Naturais", "Geografia"],
                "Sofia Rodrigues":["Educação Física", "Arte"],
                "Carlos Oliveira":["Ed. Moral e Religião", "História"],
            }
            teachers_map = {}
            for tname, snames in teacher_subj_map.items():
                t = Teacher(cluster_id=cluster.id, name=tname, max_daily_lessons=6)
                db.add(t); db.flush()
                teachers_map[tname] = t
                for sn in snames:
                    if sn in subjects:
                        db.add(TeacherSubject(teacher_id=t.id, subject_id=subjects[sn].id))
                db.add(TeacherSchoolAssignment(
                    teacher_id=t.id, school_id=school.id,
                    academic_year_id=year.id, travel_time_minutes=0,
                ))

            # teacher_id by subject_id (first teacher for each subject)
            teacher_by_subject: dict = {}
            for tname, snames in teacher_subj_map.items():
                t = teachers_map[tname]
                for sn in snames:
                    if sn in subjects and subjects[sn].id not in teacher_by_subject:
                        teacher_by_subject[subjects[sn].id] = t.id

            # Classes
            class_data = [
                ("5A", 5, 26), ("5B", 5, 24), ("6A", 6, 25), ("6B", 6, 22),
                ("7A", 7, 23), ("8A", 8, 24), ("9A", 9, 22),
            ]
            classes_list = []
            for cname, ylevel, nstud in class_data:
                c = Class(
                    school_id=school.id, academic_year_id=year.id,
                    name=cname, year_level=ylevel, num_students=nstud,
                )
                db.add(c); db.flush()
                classes_list.append(c)

            # Curriculum: structure maps to (split_count, consecutive_pairs)
            STRUCT = {
                "2+1":   (3, 1),  # 3 parts, 1 consecutive pair
                "1+1+1": (3, 0),  # 3 parts, none consecutive
                "1+1":   (2, 0),  # 2 parts, none consecutive
                "1":     (1, 0),  # 1 part
            }
            # (subject, hpw_for_display, structure_override_or_None)
            curriculum_56 = [
                ("Português",           5,  "2+1"),
                ("Matemática",          5,  "2+1"),
                ("Inglês",              3,  "1+1+1"),
                ("Ciências Naturais",   2,  "1+1"),
                ("História",            2,  "1+1"),
                ("Geografia",           2,  "1+1"),
                ("Educação Física",     2,  "1+1"),
                ("Arte",                2,  "1+1"),
                ("Ed. Moral e Religião",1,  "1"),
            ]
            curriculum_789 = [
                ("Português",           5,  "2+1"),
                ("Matemática",          5,  "2+1"),
                ("Inglês",              3,  "1+1+1"),
                ("Ciências Naturais",   3,  "1+1+1"),
                ("História",            3,  "1+1+1"),
                ("Geografia",           2,  "1+1"),
                ("Educação Física",     2,  "1+1"),
                ("TIC",                 2,  "1+1"),
            ]
            for cls in classes_list:
                curric = curriculum_56 if cls.year_level <= 6 else curriculum_789
                for sname, hpw, wstruct in curric:
                    if sname not in subjects:
                        continue
                    sc, cp = STRUCT.get(wstruct, (2, 0))
                    db.add(CurriculumEntry(
                        class_id=cls.id, subject_id=subjects[sname].id,
                        hours_per_week=float(hpw),
                        is_split=sc > 1, split_count=sc, consecutive_pairs=cp,
                    ))
            db.flush()

            # Scheduling rules
            # max_periods_per_day_class=6: with 7 classes and 6 teachers, 6/day lets
            # each class skip 1 weekday so at most 6 classes ever need slot-1 simultaneously
            db.add(SchedulingRules(
                cluster_id=cluster.id, academic_year_id=year.id,
                max_periods_per_day_class=6, max_periods_per_day_teacher=6,
                max_consecutive_periods_class=2, max_consecutive_periods_teacher=4,
                avoid_isolated_teacher=True, no_student_gaps=True,
                minimize_teacher_gaps=True, teacher_gap_weight=10,
                no_same_subject_twice_per_day=True, distribute_subjects_weight=5,
                students_start_slot_1=True, no_pe_after_lunch=True, lunch_after_slot=4,
            ))

            # Pre-built demo timetable
            timetable = Timetable(
                academic_year_id=year.id,
                name="Horário Demo 2025/2026",
                status="generated",
                solver_status="FEASIBLE",
                created_at=dt.datetime.utcnow(),
                updated_at=dt.datetime.utcnow(),
            )
            db.add(timetable); db.flush()
            _build_demo_timetable(db, timetable.id, classes_list, teacher_by_subject)

            db.commit()
            logger.info("Dados de demonstração criados com sucesso.")

        # Only touch the demo timetable (identified by name) — never wipe user timetables
        year = db.query(AcademicYear).filter(AcademicYear.cluster_id == cluster.id).first()
        if year:
            rules = db.query(SchedulingRules).filter(
                SchedulingRules.cluster_id == cluster.id
            ).first()
            if rules and rules.max_periods_per_day_class < 6:
                rules.max_periods_per_day_class = 6
                db.commit()
                logger.info("Demo: max_periods_per_day_class corrigido para 6 (era %d).", 5)

            demo_timetable = db.query(Timetable).filter(
                Timetable.academic_year_id == year.id,
                Timetable.name == "Horário Demo 2025/2026",
            ).first()
            if demo_timetable:
                demo_classes = db.query(Class).filter(
                    Class.school_id.in_(
                        [s.id for s in db.query(School).filter(School.cluster_id == cluster.id).all()]
                    ),
                    Class.academic_year_id == year.id,
                ).order_by(Class.id).all()
                demo_class_ids = {c.id for c in demo_classes}
                # Build teacher map restricted to demo subjects/teachers
                teacher_by_subject: dict = {}
                demo_teacher_ids = {
                    a.teacher_id for a in db.query(TeacherSchoolAssignment).filter(
                        TeacherSchoolAssignment.academic_year_id == year.id
                    ).all()
                }
                for ts in db.query(TeacherSubject).filter(
                    TeacherSubject.teacher_id.in_(list(demo_teacher_ids))
                ).all():
                    if ts.subject_id not in teacher_by_subject:
                        teacher_by_subject[ts.subject_id] = ts.teacher_id
                # Only rebuild if timetable has no lessons yet (first boot) or is the auto-seeded one
                lesson_count = db.query(ScheduledLesson).filter(
                    ScheduledLesson.timetable_id == demo_timetable.id
                ).count()
                if lesson_count == 0:
                    _build_demo_timetable(db, demo_timetable.id, demo_classes, teacher_by_subject)
                    demo_timetable.updated_at = dt.datetime.utcnow()
                    db.commit()
                    logger.info("Horário demo construído.")
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


@app.on_event("startup")
def cleanup_stuck_generating():
    """Mark any timetable left in 'generating' as 'error' — they were interrupted by a restart.
    Grace period of 3 minutes: if the heartbeat was recent, schedule the check for later."""
    from app.models.models import Timetable
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        stuck = db.query(Timetable).filter(Timetable.status == "generating").all()
        now = datetime.utcnow()
        grace = timedelta(minutes=3)
        to_mark = [t for t in stuck if (now - (t.updated_at or t.created_at)) > grace]
        recent  = [t for t in stuck if (now - (t.updated_at or t.created_at)) <= grace]
        for t in to_mark:
            t.status = "error"
            t.solver_status = "Processo interrompido — o servidor foi reiniciado durante a geração."
            logger.warning(f"Timetable {t.id} estava preso em 'generating' — marcado como erro.")
        if to_mark:
            db.commit()
        # Schedule a deferred check for recently-active ones
        for t in recent:
            tid = t.id
            logger.info(f"Timetable {tid} em 'generating' com heartbeat recente — a verificar novamente em 4 min.")
            from apscheduler.triggers.date import DateTrigger
            run_at = now + timedelta(minutes=4)
            try:
                from app.scheduler.notifications import get_scheduler
                sched = get_scheduler()
                if sched:
                    sched.add_job(
                        _deferred_cleanup, DateTrigger(run_date=run_at),
                        args=[tid], id=f"cleanup_{tid}", replace_existing=True,
                    )
            except Exception as e:
                logger.warning(f"Não foi possível agendar cleanup diferido para {tid}: {e}")
    finally:
        db.close()


def _deferred_cleanup(timetable_id: int):
    """Mark a timetable as interrupted if still 'generating' after the grace period."""
    from app.models.models import Timetable
    db = SessionLocal()
    try:
        t = db.query(Timetable).filter(Timetable.id == timetable_id).first()
        if t and t.status == "generating":
            t.status = "error"
            t.solver_status = "Processo interrompido — o servidor foi reiniciado durante a geração."
            db.commit()
            logger.warning(f"Timetable {timetable_id} continuava em 'generating' — marcado como erro (cleanup diferido).")
    finally:
        db.close()


@app.on_event("shutdown")
def stop_scheduler():
    scheduler_instance.stop_scheduler()


@app.get("/health")
async def health():
    return {"status": "ok"}
