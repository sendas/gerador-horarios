"""
OR-Tools CP-SAT scheduler engine for school timetable generation.
"""
import logging
from datetime import datetime
from collections import defaultdict
from ortools.sat.python import cp_model
from app.database import SessionLocal
from app.models.models import (
    Timetable, ScheduledLesson, CurriculumEntry, Class, Subject,
    Teacher, TeacherSubject, TeacherAvailability, TeacherSchoolAssignment,
    NonTeachingAssignment, TimeSlotConfig, Room, School
)

logger = logging.getLogger(__name__)

DAYS = [0, 1, 2, 3, 4]  # Mon-Fri


def generate_timetable(timetable_id: int):
    db = SessionLocal()
    try:
        _run_solver(db, timetable_id)
    except Exception as e:
        logger.error(f"Solver error for timetable {timetable_id}: {e}", exc_info=True)
        tt = db.query(Timetable).filter(Timetable.id == timetable_id).first()
        if tt:
            tt.status = "error"
            tt.solver_status = str(e)
            tt.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def _run_solver(db, timetable_id: int):
    tt = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not tt:
        raise ValueError(f"Timetable {timetable_id} not found")

    academic_year_id = tt.academic_year_id

    # ── Load data ────────────────────────────────────────────────────────────

    # Time slots: {(day, slot_number)} available
    slot_rows = db.query(TimeSlotConfig).filter(
        TimeSlotConfig.academic_year_id == academic_year_id,
        TimeSlotConfig.is_break == False  # noqa: E712
    ).all()
    if not slot_rows:
        tt.status = "error"
        tt.solver_status = "No time slots configured for this academic year"
        tt.updated_at = datetime.utcnow()
        db.commit()
        return

    all_slots = sorted({(r.day_of_week, r.slot_number) for r in slot_rows})
    slots_per_day = defaultdict(list)
    for d, s in all_slots:
        slots_per_day[d].append(s)

    # Curriculum entries
    entries = (
        db.query(CurriculumEntry)
        .join(Class, CurriculumEntry.class_id == Class.id)
        .filter(Class.academic_year_id == academic_year_id)
        .all()
    )
    if not entries:
        tt.status = "error"
        tt.solver_status = "No curriculum entries found for this academic year"
        tt.updated_at = datetime.utcnow()
        db.commit()
        return

    # Teachers eligible for each entry (via TeacherSubject)
    entry_teachers: dict[int, list[int]] = {}
    for entry in entries:
        ts = db.query(TeacherSubject).filter(
            TeacherSubject.subject_id == entry.subject_id
        ).all()
        teacher_ids = [t.teacher_id for t in ts]
        entry_teachers[entry.id] = teacher_ids

    # Teacher availability: blocked slots {teacher_id: set of (day, slot)}
    blocked: dict[int, set] = defaultdict(set)
    avail_rows = db.query(TeacherAvailability).filter(
        TeacherAvailability.academic_year_id == academic_year_id,
        TeacherAvailability.is_available == False  # noqa: E712
    ).all()
    for a in avail_rows:
        blocked[a.teacher_id].add((a.day_of_week, a.slot_number))

    # Non-teaching assignments also block slots for teachers
    nt_rows = db.query(NonTeachingAssignment).filter(
        NonTeachingAssignment.academic_year_id == academic_year_id
    ).all()
    for nt in nt_rows:
        blocked[nt.teacher_id].add((nt.day_of_week, nt.slot_number))

    # Teacher school assignments for travel constraint
    school_assignments = db.query(TeacherSchoolAssignment).filter(
        TeacherSchoolAssignment.academic_year_id == academic_year_id
    ).all()
    teacher_schools: dict[int, dict[int, int]] = defaultdict(dict)  # teacher_id -> {school_id: travel_time}
    for sa in school_assignments:
        teacher_schools[sa.teacher_id][sa.school_id] = sa.travel_time_minutes

    # Class -> school mapping
    class_school: dict[int, int] = {}
    for entry in entries:
        class_school[entry.class_id] = entry.class_.school_id

    # Rooms per school
    rooms_by_school: dict[int, list[int]] = defaultdict(list)
    for room in db.query(Room).all():
        rooms_by_school[room.school_id].append(room.id)

    # Teacher info
    teachers = {t.id: t for t in db.query(Teacher).all()}

    # ── Build occurrences ────────────────────────────────────────────────────
    # Each curriculum entry needs int(hours_per_week) occurrences per week
    # (handle fractional by rounding)
    occurrences: list[tuple[int, int]] = []  # (entry_id, occ_index)
    for entry in entries:
        count = entry.split_count if entry.is_split else max(1, round(entry.hours_per_week))
        for occ in range(count):
            occurrences.append((entry.id, occ))

    if not occurrences:
        tt.status = "error"
        tt.solver_status = "No lesson occurrences to schedule"
        tt.updated_at = datetime.utcnow()
        db.commit()
        return

    # ── CP-SAT model ─────────────────────────────────────────────────────────
    model = cp_model.CpModel()

    # slot_var[(entry_id, occ)] = (day, slot) as index into all_slots
    slot_indices = {ds: i for i, ds in enumerate(all_slots)}
    n_slots = len(all_slots)

    # x[(entry_id, occ, slot_idx)] = BoolVar: is this occurrence at this slot?
    x: dict[tuple, cp_model.IntVar] = {}
    for (eid, occ) in occurrences:
        for si in range(n_slots):
            x[(eid, occ, si)] = model.NewBoolVar(f"x_{eid}_{occ}_{si}")

    # t[(entry_id, occ, teacher_id)] = BoolVar: is this teacher assigned?
    t: dict[tuple, cp_model.IntVar] = {}
    for (eid, occ) in occurrences:
        for tid in entry_teachers.get(eid, []):
            t[(eid, occ, tid)] = model.NewBoolVar(f"t_{eid}_{occ}_{tid}")

    # ── Constraints ──────────────────────────────────────────────────────────

    # 1. Each occurrence is scheduled exactly once
    for (eid, occ) in occurrences:
        model.AddExactlyOne([x[(eid, occ, si)] for si in range(n_slots)])

    # 2. Each occurrence has exactly one teacher (if any teachers available)
    for (eid, occ) in occurrences:
        teacher_vars = [t[(eid, occ, tid)] for tid in entry_teachers.get(eid, []) if (eid, occ, tid) in t]
        if teacher_vars:
            model.AddExactlyOne(teacher_vars)

    # 3. No class double-booking: for each class, at most one lesson per slot
    entry_by_class: dict[int, list[int]] = defaultdict(list)
    for entry in entries:
        entry_by_class[entry.class_id].append(entry.id)

    for class_id, eids in entry_by_class.items():
        for si in range(n_slots):
            model.AddAtMostOne([
                x[(eid, occ, si)]
                for eid in eids
                for occ_idx in range(
                    next((e.split_count if e.is_split else max(1, round(e.hours_per_week))
                          for e in entries if e.id == eid), 1)
                )
                if (eid, occ_idx, si) in x
            ])

    # 4. No teacher double-booking: for each (teacher, slot), at most one lesson
    # Use auxiliary variables: a[(eid, occ, tid, si)] = x AND t
    all_teacher_ids = list(teachers.keys())
    for tid in all_teacher_ids:
        for si in range(n_slots):
            teaching_here = []
            for (eid, occ) in occurrences:
                if (eid, occ, tid) in t and (eid, occ, si) in x:
                    aux = model.NewBoolVar(f"aux_{eid}_{occ}_{tid}_{si}")
                    model.AddBoolAnd([x[(eid, occ, si)], t[(eid, occ, tid)]]).OnlyEnforceIf(aux)
                    model.AddBoolOr([x[(eid, occ, si)].Not(), t[(eid, occ, tid)].Not()]).OnlyEnforceIf(aux.Not())
                    teaching_here.append(aux)
            if len(teaching_here) > 1:
                model.AddAtMostOne(teaching_here)

    # 5. Teacher availability: if slot (day, slot) is blocked for teacher, they can't teach
    for (eid, occ) in occurrences:
        for tid in entry_teachers.get(eid, []):
            if (eid, occ, tid) not in t:
                continue
            for (day, slot) in blocked.get(tid, set()):
                if (day, slot) in slot_indices:
                    si = slot_indices[(day, slot)]
                    if (eid, occ, si) in x:
                        # If teacher is assigned AND slot is this blocked slot -> forbidden
                        model.AddImplication(t[(eid, occ, tid)], x[(eid, occ, si)].Not())

    # ── Soft constraints (objective) ─────────────────────────────────────────
    penalty_terms = []

    for tid, teacher in teachers.items():
        # Soft: preferred free day
        if teacher.preferred_free_day is not None:
            free_day = teacher.preferred_free_day
            day_slots = [si for si, (d, s) in enumerate(all_slots) if d == free_day]
            for (eid, occ) in occurrences:
                if (eid, occ, 0) not in x:
                    continue
                for si in day_slots:
                    if (eid, occ, si) not in x:
                        continue
                    if (eid, occ, tid) in t:
                        aux = model.NewBoolVar(f"pref_{eid}_{occ}_{tid}_{si}")
                        model.AddBoolAnd([x[(eid, occ, si)], t[(eid, occ, tid)]]).OnlyEnforceIf(aux)
                        model.AddBoolOr([x[(eid, occ, si)].Not(), t[(eid, occ, tid)].Not()]).OnlyEnforceIf(aux.Not())
                        penalty_terms.append(aux)

        # Soft: max_daily_lessons
        max_daily = teacher.max_daily_lessons
        for day in DAYS:
            day_slots_idx = [si for si, (d, s) in enumerate(all_slots) if d == day]
            daily_lessons = []
            for (eid, occ) in occurrences:
                for si in day_slots_idx:
                    if (eid, occ, si) in x and (eid, occ, tid) in t:
                        aux = model.NewBoolVar(f"daily_{eid}_{occ}_{tid}_{day}_{si}")
                        model.AddBoolAnd([x[(eid, occ, si)], t[(eid, occ, tid)]]).OnlyEnforceIf(aux)
                        model.AddBoolOr([x[(eid, occ, si)].Not(), t[(eid, occ, tid)].Not()]).OnlyEnforceIf(aux.Not())
                        daily_lessons.append(aux)
            if daily_lessons:
                excess = model.NewIntVar(0, len(daily_lessons), f"excess_{tid}_{day}")
                model.Add(sum(daily_lessons) - max_daily <= excess)
                model.Add(excess >= 0)
                penalty_terms.append(excess)

    if penalty_terms:
        model.Minimize(sum(penalty_terms))

    # ── Solve ─────────────────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    solver.parameters.num_workers = 4

    status = solver.Solve(model)

    # ── Persist results ───────────────────────────────────────────────────────
    db.query(ScheduledLesson).filter(ScheduledLesson.timetable_id == timetable_id).delete()

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        lessons_to_add = []
        for (eid, occ) in occurrences:
            scheduled_si = None
            for si in range(n_slots):
                if (eid, occ, si) in x and solver.Value(x[(eid, occ, si)]) == 1:
                    scheduled_si = si
                    break

            if scheduled_si is None:
                continue

            day, slot = all_slots[scheduled_si]

            assigned_teacher = None
            for tid in entry_teachers.get(eid, []):
                if (eid, occ, tid) in t and solver.Value(t[(eid, occ, tid)]) == 1:
                    assigned_teacher = tid
                    break

            # Assign a room from the class's school
            entry = next((e for e in entries if e.id == eid), None)
            assigned_room = None
            if entry:
                school_id = class_school.get(entry.class_id)
                school_rooms = rooms_by_school.get(school_id, [])
                if school_rooms:
                    assigned_room = school_rooms[0]

            lessons_to_add.append(ScheduledLesson(
                timetable_id=timetable_id,
                curriculum_entry_id=eid,
                teacher_id=assigned_teacher,
                room_id=assigned_room,
                day_of_week=day,
                slot_number=slot,
            ))

        db.add_all(lessons_to_add)
        tt.status = "generated"
        tt.solver_status = solver.StatusName(status)
    else:
        tt.status = "error"
        tt.solver_status = solver.StatusName(status)

    tt.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"Timetable {timetable_id} generation complete: {tt.solver_status}")
