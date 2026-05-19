"""
OR-Tools CP-SAT scheduler engine for school timetable generation.
"""
import logging
from datetime import datetime
from collections import defaultdict
from itertools import combinations
from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import LinearExpr
from app.database import SessionLocal
from app.models.models import (
    Timetable, ScheduledLesson, CurriculumEntry, Class, Subject,
    Teacher, TeacherSubject, TeacherAvailability, TeacherSchoolAssignment,
    NonTeachingAssignment, TimeSlotConfig, Room, School, AcademicYear,
    SchedulingRules, TimetableLock
)

logger = logging.getLogger(__name__)

DAYS = [0, 1, 2, 3, 4]  # Mon-Fri


def generate_timetable(timetable_id: int, options: dict = None):
    db = SessionLocal()
    try:
        _run_solver(db, timetable_id, options)
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


def _log(db, tt, msg: str):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    tt.generation_log = (tt.generation_log + "\n" + entry) if tt.generation_log else entry
    tt.updated_at = datetime.utcnow()
    db.commit()


def _run_solver(db, timetable_id: int, options: dict = None):
    tt = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not tt:
        raise ValueError(f"Timetable {timetable_id} not found")

    tt.generation_log = None
    db.commit()
    _log(db, tt, "A carregar dados do ano letivo...")

    academic_year_id = tt.academic_year_id

    # ── Extract generation options ────────────────────────────────────────────
    opts = options or {}
    year_levels_filter = opts.get("year_levels")  # None or list of ints
    opt_no_student_gaps = opts.get("no_student_gaps", True)
    opt_minimize_teacher_gaps = opts.get("minimize_teacher_gaps", True)
    opt_teacher_gap_weight = opts.get("teacher_gap_weight", 10)
    opt_no_same_subject_twice = opts.get("no_same_subject_twice_per_day", True)
    opt_distribute_weight = opts.get("distribute_subjects_weight", 5)
    max_time = opts.get("max_time_seconds", 120)

    # ── Load data ────────────────────────────────────────────────────────────

    # Time slots: load all (including breaks) to detect lunch
    all_slot_rows = db.query(TimeSlotConfig).filter(
        TimeSlotConfig.academic_year_id == academic_year_id,
    ).all()
    slot_rows = [r for r in all_slot_rows if not r.is_break]
    if not slot_rows:
        tt.status = "error"
        tt.solver_status = "No time slots configured for this academic year"
        tt.updated_at = datetime.utcnow()
        db.commit()
        return

    # Auto-detect lunch slot: the slot immediately before the first break slot (per day)
    break_slots = {(r.day_of_week, r.slot_number) for r in all_slot_rows if r.is_break}
    if break_slots:
        # find the minimum slot_number that is a break, across all days
        min_break_slot = min(s for (_, s) in break_slots)
        detected_lunch = min_break_slot - 1
        if detected_lunch >= 1 and "lunch_after_slot" not in opts:
            opts["lunch_after_slot"] = detected_lunch

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

    # Filter entries by year_level if specified
    if year_levels_filter:
        entries = [e for e in entries if e.class_.year_level in year_levels_filter]

    # Teachers eligible for each entry.
    # If entry.teacher_id is set, that teacher is the only option (hard assignment).
    # Otherwise fall back to TeacherSubject links.
    entry_teachers: dict[int, list[int]] = {}
    for entry in entries:
        if entry.teacher_id:
            entry_teachers[entry.id] = [entry.teacher_id]
        else:
            ts = db.query(TeacherSubject).filter(
                TeacherSubject.subject_id == entry.subject_id
            ).all()
            entry_teachers[entry.id] = [t.teacher_id for t in ts]

    # ── Entries without eligible teacher: skip (warn but continue generation) ──
    no_teacher: list[str] = []
    entries_with_teacher = []
    for entry in entries:
        if not entry_teachers.get(entry.id):
            subj_name = entry.subject.name if entry.subject else f"id={entry.subject_id}"
            class_name = entry.class_.name if entry.class_ else f"id={entry.class_id}"
            no_teacher.append(f"{class_name} · {subj_name}")
        else:
            entries_with_teacher.append(entry)
    entries = entries_with_teacher

    if no_teacher:
        skip_msg = (
            f"{len(no_teacher)} entrada(s) sem professor atribuído — excluídas da geração:\n"
            + "\n".join(f"  • {e}" for e in no_teacher[:40])
        )
        _log(db, tt, f"Aviso: {skip_msg}")
        logger.warning("Timetable %d: %d entradas sem professor ignoradas.", timetable_id, len(no_teacher))
        tt.solver_status = skip_msg
        db.commit()

    if not entries:
        tt.status = "error"
        tt.solver_status = "Nenhuma entrada com professor atribuído. Atribua professores antes de gerar."
        tt.updated_at = datetime.utcnow()
        db.commit()
        return

    _log(db, tt, f"Dados carregados: {len(entries)} entradas com professor; {len(no_teacher)} excluídas sem docente.")

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

    # Load scheduling rules for this academic year / cluster
    academic_year = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    cluster_id = academic_year.cluster_id if academic_year else None

    rules_obj = None
    if cluster_id:
        rules_obj = (
            db.query(SchedulingRules)
            .filter(
                SchedulingRules.cluster_id == cluster_id,
                (SchedulingRules.academic_year_id == academic_year_id) | (SchedulingRules.academic_year_id == None)  # noqa: E711
            )
            .order_by(SchedulingRules.academic_year_id.desc().nullslast())  # year-specific takes priority
            .first()
        )

    max_per_day_class = rules_obj.max_periods_per_day_class if rules_obj else 5
    max_per_day_teacher = rules_obj.max_periods_per_day_teacher if rules_obj else 6
    max_consec_class = rules_obj.max_consecutive_periods_class if rules_obj else 2
    max_consec_teacher = rules_obj.max_consecutive_periods_teacher if rules_obj else 4
    avoid_isolated = rules_obj.avoid_isolated_teacher if rules_obj else False

    # opts override DB rules; fall back to DB rules, then hard defaults
    if rules_obj and "students_start_slot_1" not in opts:
        opts["students_start_slot_1"] = bool(getattr(rules_obj, "students_start_slot_1", True))
    if rules_obj and "no_pe_after_lunch" not in opts:
        opts["no_pe_after_lunch"] = bool(getattr(rules_obj, "no_pe_after_lunch", True))
    if rules_obj and "lunch_after_slot" not in opts:
        opts["lunch_after_slot"] = getattr(rules_obj, "lunch_after_slot", 4) or 4

    # ── Process timetable locks ───────────────────────────────────────────────
    # Locked teachers/classes keep their existing ScheduledLessons intact.
    # Their entries are removed from the solver so only the rest is re-scheduled.
    locked_teacher_ids: set[int] = set()
    locked_class_ids: set[int] = set()
    for lock in db.query(TimetableLock).filter(TimetableLock.timetable_id == timetable_id).all():
        if lock.lock_type == "teacher":
            locked_teacher_ids.add(lock.entity_id)
        else:
            locked_class_ids.add(lock.entity_id)

    pinned_lesson_ids: set[int] = set()
    pinned_entry_ids: set[int] = set()
    blocked_class_slots: dict[int, set] = defaultdict(set)  # class_id -> {(day, slot)}

    if locked_teacher_ids or locked_class_ids:
        entries_map = {e.id: e for e in entries}
        pinned_entry_occ: dict[int, list] = defaultdict(list)

        existing_lessons = db.query(ScheduledLesson).filter(
            ScheduledLesson.timetable_id == timetable_id
        ).all()
        for lesson in existing_lessons:
            entry = entries_map.get(lesson.curriculum_entry_id)
            if not entry:
                continue
            is_locked_lesson = (
                entry.class_id in locked_class_ids or
                (lesson.teacher_id and lesson.teacher_id in locked_teacher_ids)
            )
            if is_locked_lesson:
                pinned_lesson_ids.add(lesson.id)
                pinned_entry_occ[lesson.curriculum_entry_id].append(
                    (lesson.day_of_week, lesson.slot_number, lesson.teacher_id)
                )
                blocked_class_slots[entry.class_id].add((lesson.day_of_week, lesson.slot_number))
                if lesson.teacher_id:
                    blocked[lesson.teacher_id].add((lesson.day_of_week, lesson.slot_number))

        # An entry is "fully pinned" when all its occurrences are covered by pinned lessons
        for eid, occ_list in pinned_entry_occ.items():
            entry = entries_map.get(eid)
            if entry:
                expected = entry.split_count if entry.is_split else max(1, round(entry.hours_per_week))
                if len(occ_list) >= expected:
                    pinned_entry_ids.add(eid)

        if pinned_entry_ids:
            entries = [e for e in entries if e.id not in pinned_entry_ids]
            _log(db, tt, (
                f"Bloqueados: {len(pinned_entry_ids)} entradas de "
                f"{len(locked_class_ids)} turma(s) e {len(locked_teacher_ids)} professor(es); "
                f"{len(pinned_lesson_ids)} aulas preservadas."
            ))

    # Each curriculum entry needs int(hours_per_week) occurrences per week
    # (handle fractional by rounding)
    occurrences: list[tuple[int, int]] = []  # (entry_id, occ_index)
    for entry in entries:
        count = entry.split_count if entry.is_split else max(1, round(entry.hours_per_week))
        for occ in range(count):
            occurrences.append((entry.id, occ))

    if not occurrences:
        tt.status = "error"
        tt.solver_status = "Sem ocorrências para agendar. Verifique se as turmas têm currículo."
        tt.updated_at = datetime.utcnow()
        db.commit()
        return

    # ── CP-SAT model ─────────────────────────────────────────────────────────
    model = cp_model.CpModel()

    # slot_var[(entry_id, occ)] = (day, slot) as index into all_slots
    slot_indices = {ds: i for i, ds in enumerate(all_slots)}
    n_slots = len(all_slots)

    # Precompute slot metadata
    slot_day_of = [all_slots[si][0] for si in range(n_slots)]
    slot_num_of = [all_slots[si][1] for si in range(n_slots)]

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

    # 0. Locked class slots: remaining entries of a class with pinned lessons
    #    cannot use those already-occupied slots.
    if blocked_class_slots:
        for (eid, occ) in occurrences:
            entry = next((e for e in entries if e.id == eid), None)
            if not entry:
                continue
            for (day, slot) in blocked_class_slots.get(entry.class_id, set()):
                si = slot_indices.get((day, slot))
                if si is not None and (eid, occ, si) in x:
                    model.Add(x[(eid, occ, si)] == 0)

    # 1. Each occurrence is scheduled exactly once
    for (eid, occ) in occurrences:
        model.AddExactlyOne([x[(eid, occ, si)] for si in range(n_slots)])

    # 2. Each occurrence has exactly one teacher (if any teachers available)
    for (eid, occ) in occurrences:
        teacher_vars = [t[(eid, occ, tid)] for tid in entry_teachers.get(eid, []) if (eid, occ, tid) in t]
        if teacher_vars:
            model.AddExactlyOne(teacher_vars)

    # 3. No class double-booking: for each class, at most one lesson per slot
    # Semestral pairs share a slot, so we skip counting one from each pair
    entry_by_class: dict[int, list[int]] = defaultdict(list)
    for entry in entries:
        entry_by_class[entry.class_id].append(entry.id)

    # ── Pre-solve sanity checks + auto-adjust ────────────────────────────────
    n_classes = len(entry_by_class)
    n_teachers = len(teachers)
    n_days_count = len(DAYS)
    slots_per_day_count = len(all_slots) // n_days_count if n_days_count else 0
    logger.info(
        "Timetable %d: %d turmas, %d professores, %d tempos/dia, %d ocorrências, limite=%ds",
        timetable_id, n_classes, n_teachers, slots_per_day_count, len(occurrences), max_time,
    )
    _log(db, tt, f"{n_classes} turmas · {n_teachers} professores · {len(occurrences)} ocorrências · {slots_per_day_count} tempos/dia")

    # Auto-adjust max_per_day_class when students_start_slot_1 is active and there are
    # more classes than teachers. By pigeonhole, with N classes and T teachers (N>T),
    # some day will always have N classes needing slot-1 simultaneously — impossible with
    # only T teachers. Fix: raise max_per_day so every class can skip at least 1 day.
    if opts.get("students_start_slot_1") and n_classes > n_teachers and n_days_count > 1:
        # Each class needs ceil(total_occ / (n_days-1)) lessons/day to fit in n_days-1 days
        for class_id, eids in entry_by_class.items():
            class_occ = sum(
                (e.split_count if e.is_split else max(1, round(e.hours_per_week)))
                for e in entries if e.id in eids
            )
            needed = -(-class_occ // (n_days_count - 1))  # ceiling division
            if needed > max_per_day_class:
                logger.warning(
                    "Timetable %d: auto-ajuste max_per_day_class %d→%d "
                    "(turma %d tem %d aulas e precisa de poder saltar 1 dia com %d turmas > %d professores).",
                    timetable_id, max_per_day_class, needed, class_id,
                    class_occ, n_classes, n_teachers,
                )
                max_per_day_class = needed

    for tid, teacher in teachers.items():
        occ_for_teacher = sum(1 for (eid, _) in occurrences if tid in entry_teachers.get(eid, []))
        max_weekly = teacher.max_daily_lessons * n_days_count
        if occ_for_teacher > max_weekly:
            logger.warning(
                "Timetable %d: Professor %s tem %d ocorrências mas máx semanal é %d.",
                timetable_id, teacher.name, occ_for_teacher, max_weekly,
            )

    # Build semestral pairs map: entry_id -> paired_entry_id
    semestral_pairs: dict[int, int] = {}
    for entry in entries:
        if entry.is_semestral and entry.paired_entry_id:
            semestral_pairs[entry.id] = entry.paired_entry_id

    # Subject groups (turnos): entries in the same group can share a slot
    from app.models.models import SubjectGroup as SubjectGroupModel
    group_pairs: set[tuple[int, int]] = set()  # pairs (min_eid, max_eid) that CAN share a slot
    for sg in db.query(SubjectGroupModel).filter(SubjectGroupModel.academic_year_id == academic_year_id).all():
        sg_eids = [sge.curriculum_entry_id for sge in sg.entries]
        for i, eid_a in enumerate(sg_eids):
            for eid_b in sg_eids[i + 1:]:
                group_pairs.add((min(eid_a, eid_b), max(eid_a, eid_b)))

    for class_id, eids in entry_by_class.items():
        for si in range(n_slots):
            # For semestral pairs, only count one of the two paired entries
            slot_vars_full: list[tuple[int, cp_model.IntVar]] = []
            for eid in eids:
                skip = False
                if eid in semestral_pairs:
                    paired_id = semestral_pairs[eid]
                    if paired_id < eid and paired_id in eids:  # the paired entry has lower id, it's already counted
                        skip = True
                if not skip:
                    n_occ = next((e.split_count if e.is_split else max(1, round(e.hours_per_week)) for e in entries if e.id == eid), 1)
                    for occ_idx in range(n_occ):
                        if (eid, occ_idx, si) in x:
                            slot_vars_full.append((eid, x[(eid, occ_idx, si)]))
            if len(slot_vars_full) <= 1:
                continue
            if not group_pairs:
                model.AddAtMostOne([v for _, v in slot_vars_full])
            else:
                for ii in range(len(slot_vars_full)):
                    eid_i, var_i = slot_vars_full[ii]
                    for jj in range(ii + 1, len(slot_vars_full)):
                        eid_j, var_j = slot_vars_full[jj]
                        pair_key = (min(eid_i, eid_j), max(eid_i, eid_j))
                        if pair_key not in group_pairs:
                            model.AddBoolOr([var_i.Not(), var_j.Not()])

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

    # 5c. Teacher min_start_slot / max_end_slot
    for (eid, occ) in occurrences:
        for tid in entry_teachers.get(eid, []):
            if (eid, occ, tid) not in t:
                continue
            teacher = teachers.get(tid)
            if not teacher:
                continue
            if teacher.min_start_slot is not None:
                for si, (day, slot_num) in enumerate(all_slots):
                    if slot_num < teacher.min_start_slot and (eid, occ, si) in x:
                        model.AddImplication(t[(eid, occ, tid)], x[(eid, occ, si)].Not())
            if teacher.max_end_slot is not None:
                for si, (day, slot_num) in enumerate(all_slots):
                    if slot_num > teacher.max_end_slot and (eid, occ, si) in x:
                        model.AddImplication(t[(eid, occ, tid)], x[(eid, occ, si)].Not())

    # 5d. Travel time: teacher cannot have back-to-back lessons at different schools.
    # Any teacher assigned to 2+ schools needs at least 1 free slot when switching school.
    entries_map_by_id = {e.id: e for e in entries}
    for tid in all_teacher_ids:
        t_school_ids = set(teacher_schools.get(tid, {}).keys())
        if len(t_school_ids) < 2:
            continue  # single school — no travel gap needed

        for day in DAYS:
            day_slots_sorted = sorted(
                [si for si in range(n_slots) if slot_day_of[si] == day],
                key=lambda si: slot_num_of[si],
            )
            if len(day_slots_sorted) < 2:
                continue

            # For each slot build: [(aux_var, school_id)] = "T teaches at school S at this slot"
            slot_school_aux: dict[int, list] = {}
            for si in day_slots_sorted:
                aux_list = []
                for (eid, occ) in occurrences:
                    if (eid, occ, tid) not in t or (eid, occ, si) not in x:
                        continue
                    entry_t = entries_map_by_id.get(eid)
                    if not entry_t:
                        continue
                    sch = class_school.get(entry_t.class_id)
                    if sch not in t_school_ids:
                        continue
                    aux = model.NewBoolVar(f"ttrv_{tid}_{eid}_{occ}_{si}")
                    model.AddBoolAnd([x[(eid, occ, si)], t[(eid, occ, tid)]]).OnlyEnforceIf(aux)
                    model.AddBoolOr([x[(eid, occ, si)].Not(), t[(eid, occ, tid)].Not()]).OnlyEnforceIf(aux.Not())
                    aux_list.append((aux, sch))
                slot_school_aux[si] = aux_list

            # Consecutive slot pairs: forbid switching school without a free period
            for k in range(len(day_slots_sorted) - 1):
                si_a = day_slots_sorted[k]
                si_b = day_slots_sorted[k + 1]
                for (aux_a, sch_a) in slot_school_aux.get(si_a, []):
                    for (aux_b, sch_b) in slot_school_aux.get(si_b, []):
                        if sch_a != sch_b:
                            model.AddBoolOr([aux_a.Not(), aux_b.Not()])

    # 5b. Max periods per day per class (hard constraint from scheduling rules)
    for class_id, eids in entry_by_class.items():
        for day in DAYS:
            day_slot_indices = [si for si in range(n_slots) if slot_day_of[si] == day]
            if not day_slot_indices:
                continue
            class_lessons_day = []
            for eid in eids:
                n_occ = next((e.split_count if e.is_split else max(1, round(e.hours_per_week)) for e in entries if e.id == eid), 1)
                for occ in range(n_occ):
                    for si in day_slot_indices:
                        if (eid, occ, si) in x:
                            class_lessons_day.append(x[(eid, occ, si)])
            if class_lessons_day:
                model.Add(sum(class_lessons_day) <= max_per_day_class)

    # 6. Consecutive pairs constraint (hard): entries with consecutive_pairs > 0
    # For each consecutive pair (pair_idx), occurrences occ_a = pair_idx*2 and occ_b = pair_idx*2+1
    # must be on the same day and in consecutive slot numbers.
    for entry in entries:
        if not entry.consecutive_pairs or entry.consecutive_pairs <= 0:
            continue
        for pair_idx in range(entry.consecutive_pairs):
            occ_a = pair_idx * 2
            occ_b = pair_idx * 2 + 1
            if (entry.id, occ_a, 0) not in x or (entry.id, occ_b, 0) not in x:
                continue
            # same day
            day_a = sum(slot_day_of[si] * x[(entry.id, occ_a, si)] for si in range(n_slots) if (entry.id, occ_a, si) in x)
            day_b = sum(slot_day_of[si] * x[(entry.id, occ_b, si)] for si in range(n_slots) if (entry.id, occ_b, si) in x)
            # consecutive slot numbers
            num_a = sum(slot_num_of[si] * x[(entry.id, occ_a, si)] for si in range(n_slots) if (entry.id, occ_a, si) in x)
            num_b = sum(slot_num_of[si] * x[(entry.id, occ_b, si)] for si in range(n_slots) if (entry.id, occ_b, si) in x)
            model.Add(day_a == day_b)
            model.Add(num_b == num_a + 1)  # occ_b immediately after occ_a

    # 7. Semestral paired subjects must share the same time slot (all occurrences)
    processed_semestral: set[int] = set()
    for entry in entries:
        if not entry.is_semestral or not entry.paired_entry_id:
            continue
        if entry.id in processed_semestral:
            continue
        paired = next((e for e in entries if e.id == entry.paired_entry_id), None)
        if not paired:
            continue
        processed_semestral.add(entry.id)
        processed_semestral.add(paired.id)
        # Force them to share the same slots across all occurrences
        n_a = entry.split_count if entry.is_split else max(1, round(entry.hours_per_week))
        n_b = paired.split_count if paired.is_split else max(1, round(paired.hours_per_week))
        for si in range(n_slots):
            sum_a = [x[(entry.id, occ, si)] for occ in range(n_a) if (entry.id, occ, si) in x]
            sum_b = [x[(paired.id, occ, si)] for occ in range(n_b) if (paired.id, occ, si) in x]
            if sum_a and sum_b:
                model.Add(sum(sum_a) == sum(sum_b))
            elif sum_a:
                model.Add(sum(sum_a) == 0)
            elif sum_b:
                model.Add(sum(sum_b) == 0)

    # 8. No student gaps: for each class on each day, lessons must be contiguous
    if opt_no_student_gaps:
        for class_id, eids in entry_by_class.items():
            for day in DAYS:
                day_slots_sorted = sorted(
                    [si for si in range(n_slots) if slot_day_of[si] == day],
                    key=lambda si: slot_num_of[si]
                )
                if len(day_slots_sorted) < 3:
                    continue
                # is_used[si] = class has a lesson here
                is_used_map = {}
                for si in day_slots_sorted:
                    occ_vars = [
                        x[(eid, occ, si)]
                        for eid in eids
                        for occ in range(next((
                            e.split_count if e.is_split else max(1, round(e.hours_per_week))
                            for e in entries if e.id == eid), 1))
                        if (eid, occ, si) in x
                    ]
                    if not occ_vars:
                        is_used_map[si] = model.NewConstant(0)
                    else:
                        used_v = model.NewBoolVar(f"used_c{class_id}_d{day}_s{si}")
                        model.AddBoolOr(occ_vars).OnlyEnforceIf(used_v)
                        model.AddBoolAnd([v.Not() for v in occ_vars]).OnlyEnforceIf(used_v.Not())
                        is_used_map[si] = used_v
                # No gaps: if slots j and k used, all between must be used
                n_day = len(day_slots_sorted)
                for ji in range(n_day):
                    for ki in range(ji + 2, n_day):
                        for ii in range(ji + 1, ki):
                            sj = day_slots_sorted[ji]
                            sk = day_slots_sorted[ki]
                            si = day_slots_sorted[ii]
                            model.Add(
                                is_used_map[sj] + is_used_map[sk] <= is_used_map[si] + 1
                            )

    # 9. No same subject twice per day
    # Entries with consecutive_pairs > 0 need exactly 2 occurrences on the same day
    # (the consecutive pair itself), so the per-day cap is 2 for those entries.
    if opt_no_same_subject_twice:
        for entry in entries:
            n_occ = entry.split_count if entry.is_split else max(1, round(entry.hours_per_week))
            if n_occ <= 1:
                continue
            cp = getattr(entry, 'consecutive_pairs', 0) or 0
            max_per_day_entry = 2 if cp > 0 else 1
            for day in DAYS:
                day_slot_indices = [si for si in range(n_slots) if slot_day_of[si] == day]
                day_vars = [
                    x[(entry.id, occ, si)]
                    for occ in range(n_occ)
                    for si in day_slot_indices
                    if (entry.id, occ, si) in x
                ]
                if day_vars:
                    model.Add(sum(day_vars) <= max_per_day_entry)

    # 10. Students start at slot 1: first slot of each day must be used if class has any lesson
    if opts.get("students_start_slot_1", True):
        for class_id, eids in entry_by_class.items():
            for day in DAYS:
                day_slots_sorted = sorted(
                    [si for si in range(n_slots) if slot_day_of[si] == day],
                    key=lambda si: slot_num_of[si]
                )
                if len(day_slots_sorted) < 2:
                    continue
                first_si = day_slots_sorted[0]

                def make_used(si, eids_=eids):
                    occ_vars = [
                        x[(eid, occ, si)]
                        for eid in eids_
                        for occ in range(next((
                            e.split_count if e.is_split else max(1, round(e.hours_per_week))
                            for e in entries if e.id == eid), 1))
                        if (eid, occ, si) in x
                    ]
                    if not occ_vars:
                        return model.NewConstant(0)
                    v = model.NewBoolVar(f"strt_c{class_id}_d{day}_s{si}")
                    model.AddBoolOr(occ_vars).OnlyEnforceIf(v)
                    model.AddBoolAnd([u.Not() for u in occ_vars]).OnlyEnforceIf(v.Not())
                    return v

                used_first = make_used(first_si)
                for si in day_slots_sorted[1:]:
                    used_later = make_used(si)
                    # if any later slot used -> first slot must be used
                    model.Add(used_later <= used_first)

    # 11. No PE after lunch
    lunch_slot = opts.get("lunch_after_slot", 4)
    if opts.get("no_pe_after_lunch", True):
        pe_entry_ids = {
            e.id for e in entries
            if e.subject and getattr(e.subject, 'is_physical_education', False)
        }
        for eid in pe_entry_ids:
            entry = next((e for e in entries if e.id == eid), None)
            if not entry:
                continue
            n_occ = entry.split_count if entry.is_split else max(1, round(entry.hours_per_week))
            for occ in range(n_occ):
                for si in range(n_slots):
                    if slot_num_of[si] > lunch_slot and (eid, occ, si) in x:
                        model.Add(x[(eid, occ, si)] == 0)

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

        # Soft: max_daily_lessons (combining teacher's own limit with global rule)
        max_daily = min(teacher.max_daily_lessons, max_per_day_teacher)
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

    # Soft: avoid isolated periods for teachers
    if avoid_isolated:
        for tid in all_teacher_ids:
            for day in DAYS:
                day_slots_sorted = sorted(
                    [si for si in range(n_slots) if slot_day_of[si] == day],
                    key=lambda si: slot_num_of[si]
                )
                for k, si in enumerate(day_slots_sorted):
                    prev_si = day_slots_sorted[k - 1] if k > 0 else None
                    next_si = day_slots_sorted[k + 1] if k < len(day_slots_sorted) - 1 else None
                    for (eid, occ) in occurrences:
                        if (eid, occ, si) not in x or (eid, occ, tid) not in t:
                            continue
                        # aux_here = x AND t
                        aux_here = model.NewBoolVar(f"iso_here_{eid}_{occ}_{tid}_{si}")
                        model.AddBoolAnd([x[(eid, occ, si)], t[(eid, occ, tid)]]).OnlyEnforceIf(aux_here)
                        model.AddBoolOr([x[(eid, occ, si)].Not(), t[(eid, occ, tid)].Not()]).OnlyEnforceIf(aux_here.Not())
                        # Check if any adjacent slot has a lesson for this teacher
                        adj_teaching = []
                        for adj_si in [prev_si, next_si]:
                            if adj_si is None:
                                continue
                            for (eid2, occ2) in occurrences:
                                if (eid2, occ2, adj_si) in x and (eid2, occ2, tid) in t:
                                    aux_adj = model.NewBoolVar(f"adj_{eid}_{occ}_{tid}_{si}_{eid2}_{occ2}_{adj_si}")
                                    model.AddBoolAnd([x[(eid2, occ2, adj_si)], t[(eid2, occ2, tid)]]).OnlyEnforceIf(aux_adj)
                                    model.AddBoolOr([x[(eid2, occ2, adj_si)].Not(), t[(eid2, occ2, tid)].Not()]).OnlyEnforceIf(aux_adj.Not())
                                    adj_teaching.append(aux_adj)
                        if adj_teaching:
                            # is_isolated = aux_here AND (none of adj_teaching)
                            is_isolated = model.NewBoolVar(f"isol_{eid}_{occ}_{tid}_{si}")
                            model.AddBoolAnd([aux_here] + [v.Not() for v in adj_teaching]).OnlyEnforceIf(is_isolated)
                            model.AddBoolOr([aux_here.Not()] + adj_teaching).OnlyEnforceIf(is_isolated.Not())
                            penalty_terms.append(is_isolated)

    # Soft: preferred shift (morning/afternoon)
    for tid, teacher in teachers.items():
        if not teacher.preferred_shift:
            continue
        for day in DAYS:
            day_slots_list = sorted([si for si in range(n_slots) if slot_day_of[si] == day])
            if not day_slots_list:
                continue
            half = len(day_slots_list) // 2
            if teacher.preferred_shift == 'morning':
                penalty_slots = day_slots_list[half:]  # penalize afternoon slots
            else:
                penalty_slots = day_slots_list[:half]  # penalize morning slots
            for (eid, occ) in occurrences:
                for si in penalty_slots:
                    if (eid, occ, si) in x and (eid, occ, tid) in t:
                        aux = model.NewBoolVar(f"shift_{eid}_{occ}_{tid}_{si}")
                        model.AddBoolAnd([x[(eid, occ, si)], t[(eid, occ, tid)]]).OnlyEnforceIf(aux)
                        model.AddBoolOr([x[(eid, occ, si)].Not(), t[(eid, occ, tid)].Not()]).OnlyEnforceIf(aux.Not())
                        penalty_terms.append(aux)

    # Soft: minimize teacher gaps
    if opt_minimize_teacher_gaps and opt_teacher_gap_weight > 0:
        for tid in all_teacher_ids:
            for day in DAYS:
                day_slots_sorted = sorted(
                    [si for si in range(n_slots) if slot_day_of[si] == day],
                    key=lambda si: slot_num_of[si]
                )
                if len(day_slots_sorted) < 3:
                    continue
                # teacher_at[si] = BoolVar: teacher has a lesson here
                teacher_at = {}
                for si in day_slots_sorted:
                    t_vars_here = []
                    for (eid, occ) in occurrences:
                        if (eid, occ, si) in x and (eid, occ, tid) in t:
                            aux = model.NewBoolVar(f"tgap_at_{tid}_{day}_{si}_{eid}_{occ}")
                            model.AddBoolAnd([x[(eid, occ, si)], t[(eid, occ, tid)]]).OnlyEnforceIf(aux)
                            model.AddBoolOr([x[(eid, occ, si)].Not(), t[(eid, occ, tid)].Not()]).OnlyEnforceIf(aux.Not())
                            t_vars_here.append(aux)
                    if not t_vars_here:
                        teacher_at[si] = model.NewConstant(0)
                    else:
                        at_v = model.NewBoolVar(f"tgap_used_{tid}_{day}_{si}")
                        model.AddBoolOr(t_vars_here).OnlyEnforceIf(at_v)
                        model.AddBoolAnd([v.Not() for v in t_vars_here]).OnlyEnforceIf(at_v.Not())
                        teacher_at[si] = at_v
                # Penalize each gap slot (slot between first and last teacher lesson that is free)
                n_day = len(day_slots_sorted)
                for ji in range(n_day):
                    for ki in range(ji + 2, n_day):
                        for ii in range(ji + 1, ki):
                            sj = day_slots_sorted[ji]
                            sk = day_slots_sorted[ki]
                            si_mid = day_slots_sorted[ii]
                            # gap = teacher_at[sj] AND teacher_at[sk] AND NOT teacher_at[si_mid]
                            gap_v = model.NewBoolVar(f"gap_{tid}_{day}_{sj}_{si_mid}_{sk}")
                            model.AddBoolAnd([
                                teacher_at[sj], teacher_at[sk], teacher_at[si_mid].Not()
                            ]).OnlyEnforceIf(gap_v)
                            model.AddBoolOr([
                                teacher_at[sj].Not(), teacher_at[sk].Not(), teacher_at[si_mid]
                            ]).OnlyEnforceIf(gap_v.Not())
                            penalty_terms.append(LinearExpr.Term(gap_v, opt_teacher_gap_weight))

    # Soft: prefer different days for split occurrences
    if opt_distribute_weight > 0:
        for entry in entries:
            n_occ = entry.split_count if entry.is_split else max(1, round(entry.hours_per_week))
            if n_occ <= 1:
                continue
            for day in DAYS:
                day_slot_indices = [si for si in range(n_slots) if slot_day_of[si] == day]
                for occ_a, occ_b in combinations(range(n_occ), 2):
                    # Penalize if both occ_a and occ_b land on same day
                    vars_a = [x[(entry.id, occ_a, si)] for si in day_slot_indices if (entry.id, occ_a, si) in x]
                    vars_b = [x[(entry.id, occ_b, si)] for si in day_slot_indices if (entry.id, occ_b, si) in x]
                    if not vars_a or not vars_b:
                        continue
                    on_day_a = model.NewBoolVar(f"distA_{entry.id}_{occ_a}_{day}")
                    on_day_b = model.NewBoolVar(f"distB_{entry.id}_{occ_b}_{day}")
                    model.AddBoolOr(vars_a).OnlyEnforceIf(on_day_a)
                    model.AddBoolAnd([v.Not() for v in vars_a]).OnlyEnforceIf(on_day_a.Not())
                    model.AddBoolOr(vars_b).OnlyEnforceIf(on_day_b)
                    model.AddBoolAnd([v.Not() for v in vars_b]).OnlyEnforceIf(on_day_b.Not())
                    both_day = model.NewBoolVar(f"distBoth_{entry.id}_{occ_a}_{occ_b}_{day}")
                    model.AddBoolAnd([on_day_a, on_day_b]).OnlyEnforceIf(both_day)
                    model.AddBoolOr([on_day_a.Not(), on_day_b.Not()]).OnlyEnforceIf(both_day.Not())
                    penalty_terms.append(LinearExpr.Term(both_day, opt_distribute_weight))

    if penalty_terms:
        model.Minimize(sum(penalty_terms))

    # ── Solve ─────────────────────────────────────────────────────────────────
    n_bool_vars = len(x) + len(t)
    logger.info(
        "Timetable %d: a resolver modelo CP-SAT (%d BoolVars, limite=%ds, workers=4)…",
        timetable_id, n_bool_vars, max_time,
    )
    _log(db, tt, f"Modelo criado: {n_bool_vars} variáveis booleanas. A resolver... (limite: {max_time}s)")

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(max_time)
    solver.parameters.num_workers = 4

    status = solver.Solve(model)

    logger.info(
        "Timetable %d: solver terminou — status=%s, tempo=%.1fs, objective=%s",
        timetable_id,
        solver.StatusName(status),
        solver.WallTime(),
        solver.ObjectiveValue() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else "n/a",
    )
    _log(db, tt, f"Solver: {solver.StatusName(status)} em {solver.WallTime():.1f}s")

    # ── Persist results ───────────────────────────────────────────────────────
    # Only wipe existing lessons when we have a new valid solution to replace them.
    # On failure the previous timetable (if any) is preserved intact.
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
                semester=entry.semester if entry and entry.is_semestral else None,
            ))

        if pinned_lesson_ids:
            # Delete only non-pinned lessons; keep the locked ones intact
            db.query(ScheduledLesson).filter(
                ScheduledLesson.timetable_id == timetable_id,
                ScheduledLesson.id.notin_(pinned_lesson_ids),
            ).delete(synchronize_session=False)
        else:
            db.query(ScheduledLesson).filter(ScheduledLesson.timetable_id == timetable_id).delete()
        db.add_all(lessons_to_add)
        tt.status = "generated"
        tt.solver_status = solver.StatusName(status)
        _log(db, tt, f"Completo: {len(lessons_to_add)} novas aulas + {len(pinned_lesson_ids)} bloqueadas preservadas.")
    else:
        tt.status = "error"
        status_name = solver.StatusName(status)
        if status == cp_model.UNKNOWN:
            hint = (
                f"UNKNOWN — sem solução em {solver.WallTime():.0f}s. "
                "Tente: aumentar o tempo de cálculo, reduzir restrições rígidas, "
                "ou verificar se os professores têm disponibilidade suficiente."
            )
        elif status == cp_model.INFEASIBLE:
            hint = (
                "INFEASIBLE — modelo sem solução possível. Verifique: "
                "disponibilidade dos professores, 'Alunos entram no 1.º tempo' com muitas turmas, "
                "disciplinas sem professor atribuído."
            )
        else:
            hint = status_name
        tt.solver_status = hint
        logger.error("Timetable %d: %s", timetable_id, hint)

    tt.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"Timetable {timetable_id} generation complete: {tt.solver_status}")
