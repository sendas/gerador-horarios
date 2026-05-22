"""
OR-Tools CP-SAT scheduler engine for school timetable generation.
"""
import logging
import os
import multiprocessing
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
    from app.notifications import notify_timetable_done
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
        try:
            tt = db.query(Timetable).filter(Timetable.id == timetable_id).first()
            if tt:
                notify_timetable_done(db, tt.name, tt.status, tt.solver_status or "")
        except Exception:
            pass
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

    # ── Extract generation options ────────────────────────────────────────────
    opts = dict(options) if options else {}

    # Internal flags for auto-retry (not user-facing)
    _preserve_log   = opts.pop('_preserve_log',   False)
    _relaxed_retry  = opts.pop('_relaxed_retry',  False)
    _relaxed_labels = opts.pop('_relaxed_labels', [])

    if not _preserve_log:
        tt.generation_log = None
        db.commit()
    _log(db, tt, "A carregar dados do ano letivo...")

    academic_year_id = tt.academic_year_id
    year_levels_filter = opts.get("year_levels")  # None or list of ints
    school_ids_filter  = opts.get("school_ids")   # None or list of ints
    class_ids_filter   = opts.get("class_ids")    # None or list of ints (most specific — overrides others)
    opt_no_student_gaps = opts.get("no_student_gaps", True)
    opt_minimize_teacher_gaps = opts.get("minimize_teacher_gaps", True)
    opt_teacher_gap_weight = opts.get("teacher_gap_weight", 10)
    opt_no_same_subject_twice = opts.get("no_same_subject_twice_per_day", True)
    opt_distribute_weight = opts.get("distribute_subjects_weight", 5)
    max_time = opts.get("max_time_seconds", 120)

    # ── Load data ────────────────────────────────────────────────────────────

    # Determine which schools are in scope so we can pick their time-slot config.
    # class_ids_filter (most specific) → look up parent schools from DB.
    # school_ids_filter → use directly.
    # Neither → all schools (generate everything).
    if class_ids_filter:
        scope_classes = db.query(Class).filter(Class.id.in_(class_ids_filter)).all()
        schools_in_scope: set[int] | None = {c.school_id for c in scope_classes if c.school_id}
    elif school_ids_filter:
        schools_in_scope = set(school_ids_filter)
    else:
        schools_in_scope = None

    # Time slots: load all rows for the academic year, then select per-school.
    # If a school has its own specific rows (school_id = that school's id), use those.
    # Otherwise fall back to global rows (school_id IS NULL).
    # This prevents school A's slot config from corrupting school B's generation.
    _all_slot_rows = db.query(TimeSlotConfig).filter(
        TimeSlotConfig.academic_year_id == academic_year_id,
    ).all()

    _global_rows: list = [r for r in _all_slot_rows if r.school_id is None]
    _by_school: dict = defaultdict(list)
    for r in _all_slot_rows:
        if r.school_id is not None:
            _by_school[r.school_id].append(r)

    if schools_in_scope:
        selected_rows: list = []
        slot_source_desc: list[str] = []
        for sid in sorted(schools_in_scope):
            specific = _by_school.get(sid)
            if specific:
                selected_rows.extend(specific)
                n_teaching = len([r for r in specific if not r.is_break])
                logger.info("Timetable %d: escola %d → %d tempos específicos", timetable_id, sid, n_teaching)
                school_obj = db.query(School).filter(School.id == sid).first()
                sname = school_obj.name if school_obj else str(sid)
                slot_source_desc.append(f"{sname}: {n_teaching} tempos específicos")
            else:
                selected_rows.extend(_global_rows)
                n_teaching = len([r for r in _global_rows if not r.is_break])
                logger.info("Timetable %d: escola %d → %d tempos globais", timetable_id, sid, n_teaching)
                school_obj = db.query(School).filter(School.id == sid).first()
                sname = school_obj.name if school_obj else str(sid)
                slot_source_desc.append(f"{sname}: {n_teaching} tempos globais")
        all_slot_rows = selected_rows
        _log(db, tt, "Tempos letivos: " + " | ".join(slot_source_desc))
    else:
        all_slot_rows = _all_slot_rows

    slot_rows = [r for r in all_slot_rows if not r.is_break]
    if not slot_rows:
        msg = (
            "Sem tempos letivos configurados para este ano letivo"
            + (f" (escolas: {sorted(schools_in_scope)})" if schools_in_scope else "")
            + ". Configure os tempos em /time-slots."
        )
        tt.status = "error"
        tt.solver_status = msg
        tt.updated_at = datetime.utcnow()
        db.commit()
        return

    # Auto-detect lunch slot: the slot immediately before the first break slot (per day)
    break_slots = {(r.day_of_week, r.slot_number) for r in all_slot_rows if r.is_break}
    if break_slots:
        min_break_slot = min(s for (_, s) in break_slots)
        detected_lunch = min_break_slot - 1
        if detected_lunch >= 1 and "lunch_after_slot" not in opts:
            opts["lunch_after_slot"] = detected_lunch

    all_slots = sorted({(r.day_of_week, r.slot_number) for r in slot_rows})
    slots_per_day = defaultdict(list)
    for d, s in all_slots:
        slots_per_day[d].append(s)

    # Validate slot distribution: flag suspiciously low per-day counts early.
    n_active_days = len(slots_per_day)
    _max_slots_day = max((len(v) for v in slots_per_day.values()), default=0)
    if n_active_days < 3 or _max_slots_day < 2:
        school_hint = f" (escola(s) {sorted(schools_in_scope)})" if schools_in_scope else ""
        per_day_detail = ", ".join(
            f"dia {d}: {len(slots_per_day[d])}" for d in sorted(slots_per_day)
        ) or "nenhum"
        msg = (
            f"Configuração de tempos letivos insuficiente{school_hint}: "
            f"{n_active_days} dia(s) com tempos [{per_day_detail}]. "
            "Configure pelo menos 3 dias com 2+ tempos letivos em /time-slots."
        )
        tt.status = "error"
        tt.solver_status = msg
        tt.updated_at = datetime.utcnow()
        db.commit()
        _log(db, tt, f"Erro: {msg}")
        return

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

    # Filter entries: class_ids is most specific (explicit list wins); otherwise combine year + school
    if class_ids_filter:
        entries = [e for e in entries if e.class_id in class_ids_filter]
    else:
        if year_levels_filter:
            entries = [e for e in entries if e.class_.year_level in year_levels_filter]
        if school_ids_filter:
            entries = [e for e in entries if e.class_.school_id in school_ids_filter]

    # Pre-compute teacher → allowed schools (from school assignments for this year).
    # Teachers with NO assignments are unrestricted (legacy / backward compat).
    _sa_pre = db.query(TeacherSchoolAssignment).filter(
        TeacherSchoolAssignment.academic_year_id == academic_year_id
    ).all()
    teacher_allowed_schools: dict[int, set[int]] = {}
    for _sa in _sa_pre:
        teacher_allowed_schools.setdefault(_sa.teacher_id, set()).add(_sa.school_id)

    # Pre-compute class → school
    class_school_pre: dict[int, int] = {
        e.class_id: e.class_.school_id for e in entries if e.class_
    }

    # Teachers eligible for each entry.
    # Hard assignment (entry.teacher_id) takes priority.
    # Otherwise: TeacherSubject candidates filtered to teachers who are
    # assigned to the class's school (or unrestricted if no assignments).
    entry_teachers: dict[int, list[int]] = {}
    for entry in entries:
        class_school_id = class_school_pre.get(entry.class_id)
        if entry.teacher_id:
            entry_teachers[entry.id] = [entry.teacher_id]
        else:
            ts = db.query(TeacherSubject).filter(
                TeacherSubject.subject_id == entry.subject_id
            ).all()
            eligible = []
            for t in ts:
                allowed = teacher_allowed_schools.get(t.teacher_id)
                if allowed is None:
                    # No school assignments → unrestricted
                    eligible.append(t.teacher_id)
                elif class_school_id and class_school_id in allowed:
                    eligible.append(t.teacher_id)
            entry_teachers[entry.id] = eligible

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

    # Teacher info — only load teachers that are actually involved in the occurrences
    # being scheduled (directly assigned or candidates). Loading all teachers causes
    # misleading diagnostics and unnecessary soft-constraint variables in the solver.
    relevant_teacher_ids: set[int] = set()
    for tid_list in entry_teachers.values():
        relevant_teacher_ids.update(tid_list)
    teachers = {
        t.id: t
        for t in db.query(Teacher).filter(Teacher.id.in_(relevant_teacher_ids)).all()
    }

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
    avoid_isolated = rules_obj.avoid_isolated_teacher if rules_obj else True

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

    # slot_indices[(day, slot)] = integer index into all_slots list
    slot_indices = {ds: i for i, ds in enumerate(all_slots)}
    n_slots = len(all_slots)

    # Precompute slot metadata
    slot_day_of = [all_slots[si][0] for si in range(n_slots)]
    slot_num_of = [all_slots[si][1] for si in range(n_slots)]

    # ── Fixed-teacher optimisation ────────────────────────────────────────────
    # When every entry has exactly one possible teacher (the common case after
    # teacher assignment), we can skip t-variables entirely and express teacher
    # double-booking as AddAtMostOne directly on x-variables. This eliminates
    # ~N_OCC × N_SLOTS auxiliary BoolVars and speeds up the solver significantly.
    all_fixed = all(len(entry_teachers.get(e.id, [])) == 1 for e in entries)
    teacher_of: dict[tuple, int] = {}
    occ_by_teacher: dict[int, list] = defaultdict(list)
    if all_fixed:
        for (eid, occ) in occurrences:
            tid = entry_teachers[eid][0]
            teacher_of[(eid, occ)] = tid
            occ_by_teacher[tid].append((eid, occ))

    # Pre-prune allowed slots per occurrence: skip slots where the (fixed) teacher
    # is blocked, so we never create x-variables we'd immediately force to 0.
    _allowed: dict[tuple, set] = {}
    for (eid, occ) in occurrences:
        if all_fixed:
            tid = teacher_of[(eid, occ)]
            _blk: set = set(blocked.get(tid, set()))
            _t = teachers.get(tid)
            if _t:
                if _t.min_start_slot is not None:
                    _blk |= {(d, s) for d, s in all_slots if s < _t.min_start_slot}
                if _t.max_end_slot is not None:
                    _blk |= {(d, s) for d, s in all_slots if s > _t.max_end_slot}
            _allowed[(eid, occ)] = {slot_indices[ds] for ds in all_slots if ds not in _blk}
        else:
            _allowed[(eid, occ)] = set(range(n_slots))

    # x[(entry_id, occ, slot_idx)] = BoolVar: is this occurrence at this slot?
    x: dict[tuple, cp_model.IntVar] = {}
    for (eid, occ) in occurrences:
        for si in _allowed[(eid, occ)]:
            x[(eid, occ, si)] = model.NewBoolVar(f"x_{eid}_{occ}_{si}")

    # ── slot_var: channeled IntVar per occurrence (fixed-teacher mode only) ────
    # slot_var[(eid, occ)] = slot index chosen for this occurrence.
    # Channeled via: slot_var == Σ si * x[(eid, occ, si)]
    # Enables AddAllDifferent per teacher/class — much stronger propagation
    # than per-slot AddAtMostOne (Hall's theorem reasoning across all occurrences).
    slot_var: dict[tuple, cp_model.IntVar] = {}
    if all_fixed:
        for (eid, occ) in occurrences:
            allowed = sorted(_allowed[(eid, occ)])
            if not allowed:
                continue
            sv = model.NewIntVarFromDomain(
                cp_model.Domain.FromValues(allowed), f"sv_{eid}_{occ}"
            )
            slot_var[(eid, occ)] = sv
            model.Add(sv == sum(si * x[(eid, occ, si)] for si in allowed if (eid, occ, si) in x))

    # t[(entry_id, occ, teacher_id)] = BoolVar: is this teacher assigned?
    # In fixed-teacher mode these are not needed; we use x directly.
    t: dict[tuple, cp_model.IntVar] = {}
    if not all_fixed:
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
        allowed_vars = [x[(eid, occ, si)] for si in _allowed[(eid, occ)] if (eid, occ, si) in x]
        if not allowed_vars:
            tt.status = "error"
            tt.solver_status = f"Sem slots disponíveis para entrada {eid} (ocorrência {occ}) — verifique disponibilidade do professor."
            tt.updated_at = datetime.utcnow()
            db.commit()
            _log(db, tt, f"Erro: nenhum slot permitido para entrada {eid}. Verifique disponibilidade do professor.")
            return
        model.AddExactlyOne(allowed_vars)

    # 2. Each occurrence has exactly one teacher (variable-teacher mode only)
    if not all_fixed:
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
    n_days_count = len(slots_per_day)  # number of distinct days with at least one slot
    slots_per_day_min = min(len(v) for v in slots_per_day.values()) if slots_per_day else 0
    slots_per_day_max = max(len(v) for v in slots_per_day.values()) if slots_per_day else 0
    slots_per_day_count = slots_per_day_min  # conservative: worst-case day
    day_counts_str = ",".join(str(len(slots_per_day[d])) for d in sorted(slots_per_day))
    logger.info(
        "Timetable %d: %d turmas, %d professores, tempos/dia=[%s], %d ocorrências, limite=%ds",
        timetable_id, n_classes, n_teachers, day_counts_str, len(occurrences), max_time,
    )
    _log(db, tt, f"{n_classes} turmas · {n_teachers} professores · {len(occurrences)} ocorrências · {slots_per_day_count}–{slots_per_day_max} tempos/dia")

    # ── Detect obvious impossibilities before handing to solver ─────────────────

    # Log per-class load summary for diagnostics
    total_slots = len(all_slots)
    load_lines: list[str] = []
    for class_id, eids in entry_by_class.items():
        class_occ = sum(
            (e.split_count if e.is_split else max(1, round(e.hours_per_week)))
            for e in entries if e.id in eids
        )
        cls = next((e.class_ for e in entries if e.class_id == class_id), None)
        cls_name = cls.name if cls else f"id={class_id}"
        daily_avg = class_occ / n_days_count if n_days_count else 0
        flag = " ⚠" if class_occ > max_per_day_class * n_days_count else ""
        load_lines.append(f"  {cls_name}: {class_occ} aulas ({daily_avg:.1f}/dia){flag}")
    _log(db, tt, "Carga por turma (máx. " + str(max_per_day_class) + "/dia × " + str(n_days_count) + " dias = " + str(max_per_day_class * n_days_count) + " slots):\n" + "\n".join(load_lines))

    early_errors: list[str] = []

    # A. "Máx. 1 por dia" + entry with more occurrences than school days → impossible
    if opt_no_same_subject_twice:
        for entry in entries:
            n_occ = entry.split_count if entry.is_split else max(1, round(entry.hours_per_week))
            cp = getattr(entry, 'consecutive_pairs', 0) or 0
            max_per_day_entry = 2 if cp > 0 else 1
            min_days_needed = -(-n_occ // max_per_day_entry)  # ceil(n_occ / max_per_day)
            if min_days_needed > n_days_count:
                cls_name = entry.class_.name if entry.class_ else f"id={entry.class_id}"
                subj_name = entry.subject.name if entry.subject else f"id={entry.subject_id}"
                early_errors.append(
                    f"  • {cls_name} · {subj_name}: {n_occ} aulas/semana com máx. {max_per_day_entry}/dia "
                    f"precisaria de {min_days_needed} dias (só existem {n_days_count})"
                )

    if early_errors:
        msg = (
            f"INFEASIBLE antecipado — {len(early_errors)} disciplina(s) impossíveis de distribuir "
            f"com a restrição 'Máximo 1 tempo por disciplina por dia':\n"
            + "\n".join(early_errors[:20])
            + ("\n  (e mais…)" if len(early_errors) > 20 else "")
            + "\n\nSoluções: aumentar o nº de dias letivos, reduzir as horas/semana dessas "
            "disciplinas, ou desativar 'Máximo 1 tempo por disciplina por dia' no diálogo de geração."
        )
        tt.status = "error"
        tt.solver_status = msg
        tt.updated_at = datetime.utcnow()
        db.commit()
        _log(db, tt, "Erro: " + msg.split("\n")[0])
        return

    # B. Per-class overload: total occurrences exceed capacity
    overloaded_classes: list[str] = []
    for class_id, eids in entry_by_class.items():
        class_occ = sum(
            (e.split_count if e.is_split else max(1, round(e.hours_per_week)))
            for e in entries if e.id in eids
        )
        cls = next((e.class_ for e in entries if e.class_id == class_id), None)
        cls_name = cls.name if cls else f"id={class_id}"
        if class_occ > total_slots:
            overloaded_classes.append(f"  • {cls_name}: {class_occ} aulas > {total_slots} slots disponíveis")
        elif class_occ > max_per_day_class * n_days_count:
            overloaded_classes.append(
                f"  • {cls_name}: {class_occ} aulas > máximo {max_per_day_class}/dia × {n_days_count} dias = {max_per_day_class * n_days_count}"
            )

    if overloaded_classes:
        msg = (
            f"Aviso: carga horária excede o máximo permitido em {len(overloaded_classes)} turma(s) — "
            "provável causa de INFEASIBLE:\n"
            + "\n".join(overloaded_classes)
            + "\n\nSolução: aumente o máximo de aulas/dia nas Regras de Horário, "
            "ou reduza as horas/semana no currículo."
        )
        _log(db, tt, msg)
        logger.warning("Timetable %d: carga excessiva: %s", timetable_id, overloaded_classes)

    # C. Teacher overload: more occurrences than their weekly capacity
    teacher_overload: list[str] = []
    for tid, teacher in teachers.items():
        occ_for_teacher = sum(1 for (eid, _) in occurrences if tid in entry_teachers.get(eid, []))
        blocked_count = len(blocked.get(tid, set()))
        available_slots = total_slots - blocked_count
        if occ_for_teacher > available_slots:
            teacher_overload.append(
                f"  • {teacher.name}: {occ_for_teacher} aulas mas só {available_slots} slots disponíveis "
                f"({blocked_count} bloqueados)"
            )
        elif occ_for_teacher > teacher.max_daily_lessons * n_days_count:
            teacher_overload.append(
                f"  • {teacher.name}: {occ_for_teacher} aulas > máximo {teacher.max_daily_lessons}/dia × {n_days_count} dias"
            )

    if teacher_overload:
        msg = (
            f"Aviso: {len(teacher_overload)} professor(es) com carga excessiva ou disponibilidade insuficiente:\n"
            + "\n".join(teacher_overload[:10])
            + ("\n  (e mais…)" if len(teacher_overload) > 10 else "")
        )
        _log(db, tt, msg)
        logger.warning("Timetable %d: professores sobrecarregados: %d", timetable_id, len(teacher_overload))

    # D. Complexity warning: many teachers with very few lessons makes "no gaps" very hard.
    # teachers dict is already filtered to relevant teachers only; compute per-teacher occ count.
    n_active = len(teachers)
    avg_occ_per_teacher = len(occurrences) / n_active if n_active else 0
    if n_active > 20 and avg_occ_per_teacher < 5 and (opt_no_student_gaps or opts.get("students_start_slot_1", True)):
        _log(db, tt, (
            f"⚠ Aviso de complexidade: {n_active} professores ativos com média de {avg_occ_per_teacher:.1f} aulas/semana. "
            "Com muitos professores e poucas aulas cada, a restrição 'sem furos nos alunos' torna-se "
            "computacionalmente muito difícil. Se o solver não encontrar solução, desative 'Sem furos' e 'Alunos entram no 1.º tempo'."
        ))

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
    all_teacher_ids = list(teachers.keys())
    if all_fixed:
        # AddAllDifferent on slot_var per teacher (global Hall-theorem propagation) +
        # AddAtMostOne on x-vars per slot (direct binary implication, 1-hop propagation).
        # Both together are strictly stronger than either alone.
        for tid, my_occs in occ_by_teacher.items():
            svars = [slot_var[(eid, occ)] for (eid, occ) in my_occs if (eid, occ) in slot_var]
            if len(svars) > 1:
                model.AddAllDifferent(svars)
            for si in range(n_slots):
                at_si = [x[(eid, occ, si)] for (eid, occ) in my_occs if (eid, occ, si) in x]
                if len(at_si) > 1:
                    model.AddAtMostOne(at_si)
    else:
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

    # 5. Teacher availability: blocked slots forbid scheduling there.
    # In fixed-teacher mode this is already handled by pre-pruning (no x-var created
    # for blocked slots), so we only need the logic for variable-teacher mode.
    if not all_fixed:
        for (eid, occ) in occurrences:
            for tid in entry_teachers.get(eid, []):
                if (eid, occ, tid) not in t:
                    continue
                for (day, slot) in blocked.get(tid, set()):
                    if (day, slot) in slot_indices:
                        si = slot_indices[(day, slot)]
                        if (eid, occ, si) in x:
                            model.AddImplication(t[(eid, occ, tid)], x[(eid, occ, si)].Not())

    # 5c. Teacher min_start_slot / max_end_slot (also pre-pruned in fixed mode)
    if not all_fixed:
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
    entries_map_by_id = {e.id: e for e in entries}
    if all_fixed:
        # Simplified: x-vars directly represent teacher presence; no aux needed.
        for tid, my_occs in occ_by_teacher.items():
            t_school_ids = set(teacher_schools.get(tid, {}).keys())
            if len(t_school_ids) < 2:
                continue
            for day in DAYS:
                day_slots_sorted = sorted(
                    [si for si in range(n_slots) if slot_day_of[si] == day],
                    key=lambda si: slot_num_of[si],
                )
                if len(day_slots_sorted) < 2:
                    continue
                for k in range(len(day_slots_sorted) - 1):
                    si_a, si_b = day_slots_sorted[k], day_slots_sorted[k + 1]
                    for (eid_a, occ_a) in my_occs:
                        if (eid_a, occ_a, si_a) not in x:
                            continue
                        ea = entries_map_by_id.get(eid_a)
                        sch_a = class_school.get(ea.class_id) if ea else None
                        if not sch_a or sch_a not in t_school_ids:
                            continue
                        for (eid_b, occ_b) in my_occs:
                            if (eid_b, occ_b, si_b) not in x:
                                continue
                            eb = entries_map_by_id.get(eid_b)
                            sch_b = class_school.get(eb.class_id) if eb else None
                            if sch_b and sch_b != sch_a and sch_b in t_school_ids:
                                model.AddBoolOr([x[(eid_a, occ_a, si_a)].Not(), x[(eid_b, occ_b, si_b)].Not()])
    else:
        for tid in all_teacher_ids:
            t_school_ids = set(teacher_schools.get(tid, {}).keys())
            if len(t_school_ids) < 2:
                continue
            for day in DAYS:
                day_slots_sorted = sorted(
                    [si for si in range(n_slots) if slot_day_of[si] == day],
                    key=lambda si: slot_num_of[si],
                )
                if len(day_slots_sorted) < 2:
                    continue
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
                for k in range(len(day_slots_sorted) - 1):
                    si_a, si_b = day_slots_sorted[k], day_slots_sorted[k + 1]
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

    def _teacher_at_var(tid_: int, my_occs_: list, si_: int, tag: str):
        """Return a BoolVar that is 1 iff teacher tid_ teaches at slot si_."""
        tv = [x[(e, o, si_)] for (e, o) in my_occs_ if (e, o, si_) in x]
        if not tv:
            return model.NewConstant(0)
        if len(tv) == 1:
            return tv[0]
        v = model.NewBoolVar(tag)
        model.AddBoolOr(tv).OnlyEnforceIf(v)
        model.AddBoolAnd([u.Not() for u in tv]).OnlyEnforceIf(v.Not())
        return v

    if all_fixed:
        # ── Fixed-teacher soft constraints (no t-variables) ───────────────────
        for tid, my_occs in occ_by_teacher.items():
            teacher = teachers.get(tid)
            if not teacher:
                continue

            # Preferred free day
            if teacher.preferred_free_day is not None:
                for (eid, occ) in my_occs:
                    for si in range(n_slots):
                        if slot_day_of[si] == teacher.preferred_free_day and (eid, occ, si) in x:
                            penalty_terms.append(x[(eid, occ, si)])

            # Max daily lessons
            max_daily = min(teacher.max_daily_lessons, max_per_day_teacher)
            for day in DAYS:
                daily_x = [x[(eid, occ, si)] for (eid, occ) in my_occs
                            for si in range(n_slots) if slot_day_of[si] == day and (eid, occ, si) in x]
                if len(daily_x) > max_daily:
                    excess = model.NewIntVar(0, len(daily_x), f"excess_{tid}_{day}")
                    model.Add(sum(daily_x) - max_daily <= excess)
                    model.Add(excess >= 0)
                    penalty_terms.append(excess)

            # Preferred shift
            if teacher.preferred_shift:
                for day in DAYS:
                    day_sl = sorted([si for si in range(n_slots) if slot_day_of[si] == day])
                    half = len(day_sl) // 2
                    bad = day_sl[half:] if teacher.preferred_shift == 'morning' else day_sl[:half]
                    for (eid, occ) in my_occs:
                        for si in bad:
                            if (eid, occ, si) in x:
                                penalty_terms.append(x[(eid, occ, si)])

        # Maximize consecutive lessons (fixed mode):
        # For each pair of consecutive available slots (prev, curr) on the same day,
        # penalise "block-gap" = teacher teaches at curr but NOT at prev.
        # Each new lesson block costs opt_teacher_gap_weight.
        # Isolated periods (no adjacent lessons either side) cost 2× because they
        # also trigger the avoid_isolated penalty below, making them doubly unattractive.
        # This O(n) formulation replaces the previous O(n³) gap approach:
        # same optimisation direction, far fewer BoolVars, cleaner signal.
        if opt_minimize_teacher_gaps and opt_teacher_gap_weight > 0:
            for tid, my_occs in occ_by_teacher.items():
                for day in DAYS:
                    day_slots_sorted = sorted(
                        [si for si in range(n_slots) if slot_day_of[si] == day],
                        key=lambda si: slot_num_of[si]
                    )
                    if len(day_slots_sorted) < 2:
                        continue
                    teacher_at = {si: _teacher_at_var(tid, my_occs, si, f"tg_{tid}_{day}_{si}")
                                  for si in day_slots_sorted}
                    for k in range(1, len(day_slots_sorted)):
                        si_prev = day_slots_sorted[k - 1]
                        si_curr = day_slots_sorted[k]
                        at_prev = teacher_at[si_prev]
                        at_curr = teacher_at[si_curr]
                        # If teacher can never teach at either slot it's structurally fixed — skip
                        if isinstance(at_curr, int) or isinstance(at_prev, int):
                            continue
                        # block_gap = 1 iff teaches at si_curr but not at si_prev
                        block_gap = model.NewBoolVar(f"bgap_{tid}_{day}_{k}")
                        model.AddBoolAnd([at_curr, at_prev.Not()]).OnlyEnforceIf(block_gap)
                        model.AddBoolOr([at_curr.Not(), at_prev]).OnlyEnforceIf(block_gap.Not())
                        penalty_terms.append(LinearExpr.Term(block_gap, opt_teacher_gap_weight))

        # Avoid isolated periods (fixed mode):
        # penalise a slot where teacher has a lesson but NEITHER adjacent slot is used.
        # Together with block_gap this makes isolated periods cost 2× the weight.
        # Enabled when minimize_teacher_gaps is on (avoid_isolated is the DB default).
        if (opt_minimize_teacher_gaps and opt_teacher_gap_weight > 0 and avoid_isolated):
            for tid, my_occs in occ_by_teacher.items():
                for day in DAYS:
                    day_slots_sorted = sorted(
                        [si for si in range(n_slots) if slot_day_of[si] == day],
                        key=lambda si: slot_num_of[si]
                    )
                    teacher_at = {si: _teacher_at_var(tid, my_occs, si, f"iso_h_{tid}_{day}_{si}")
                                  for si in day_slots_sorted}
                    for k, si in enumerate(day_slots_sorted):
                        here = teacher_at[si]
                        if isinstance(here, int) and here == 0:
                            continue
                        adj_vs = []
                        for adj_k in [k - 1, k + 1]:
                            if 0 <= adj_k < len(day_slots_sorted):
                                adj_v = teacher_at[day_slots_sorted[adj_k]]
                                if not (isinstance(adj_v, int) and adj_v == 0):
                                    adj_vs.append(adj_v)
                        if adj_vs:
                            is_iso = model.NewBoolVar(f"iso_{tid}_{day}_{si}")
                            model.AddBoolAnd([here] + [v.Not() for v in adj_vs]).OnlyEnforceIf(is_iso)
                            model.AddBoolOr([here.Not()] + adj_vs).OnlyEnforceIf(is_iso.Not())
                            penalty_terms.append(LinearExpr.Term(is_iso, opt_teacher_gap_weight))

    else:
        # ── Variable-teacher soft constraints (original aux-variable approach) ─
        for tid, teacher in teachers.items():
            if teacher.preferred_free_day is not None:
                free_day = teacher.preferred_free_day
                day_slots = [si for si, (d, s) in enumerate(all_slots) if d == free_day]
                for (eid, occ) in occurrences:
                    for si in day_slots:
                        if (eid, occ, si) in x and (eid, occ, tid) in t:
                            aux = model.NewBoolVar(f"pref_{eid}_{occ}_{tid}_{si}")
                            model.AddBoolAnd([x[(eid, occ, si)], t[(eid, occ, tid)]]).OnlyEnforceIf(aux)
                            model.AddBoolOr([x[(eid, occ, si)].Not(), t[(eid, occ, tid)].Not()]).OnlyEnforceIf(aux.Not())
                            penalty_terms.append(aux)
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
            if teacher.preferred_shift:
                for day in DAYS:
                    day_slots_list = sorted([si for si in range(n_slots) if slot_day_of[si] == day])
                    if not day_slots_list:
                        continue
                    half = len(day_slots_list) // 2
                    penalty_slots = day_slots_list[half:] if teacher.preferred_shift == 'morning' else day_slots_list[:half]
                    for (eid, occ) in occurrences:
                        for si in penalty_slots:
                            if (eid, occ, si) in x and (eid, occ, tid) in t:
                                aux = model.NewBoolVar(f"shift_{eid}_{occ}_{tid}_{si}")
                                model.AddBoolAnd([x[(eid, occ, si)], t[(eid, occ, tid)]]).OnlyEnforceIf(aux)
                                model.AddBoolOr([x[(eid, occ, si)].Not(), t[(eid, occ, tid)].Not()]).OnlyEnforceIf(aux.Not())
                                penalty_terms.append(aux)

        if avoid_isolated:
            for tid in all_teacher_ids:
                for day in DAYS:
                    day_slots_sorted = sorted([si for si in range(n_slots) if slot_day_of[si] == day],
                                              key=lambda si: slot_num_of[si])
                    for k, si in enumerate(day_slots_sorted):
                        prev_si = day_slots_sorted[k - 1] if k > 0 else None
                        next_si = day_slots_sorted[k + 1] if k < len(day_slots_sorted) - 1 else None
                        for (eid, occ) in occurrences:
                            if (eid, occ, si) not in x or (eid, occ, tid) not in t:
                                continue
                            aux_here = model.NewBoolVar(f"iso_here_{eid}_{occ}_{tid}_{si}")
                            model.AddBoolAnd([x[(eid, occ, si)], t[(eid, occ, tid)]]).OnlyEnforceIf(aux_here)
                            model.AddBoolOr([x[(eid, occ, si)].Not(), t[(eid, occ, tid)].Not()]).OnlyEnforceIf(aux_here.Not())
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
                                is_isolated = model.NewBoolVar(f"isol_{eid}_{occ}_{tid}_{si}")
                                model.AddBoolAnd([aux_here] + [v.Not() for v in adj_teaching]).OnlyEnforceIf(is_isolated)
                                model.AddBoolOr([aux_here.Not()] + adj_teaching).OnlyEnforceIf(is_isolated.Not())
                                penalty_terms.append(is_isolated)

        if opt_minimize_teacher_gaps and opt_teacher_gap_weight > 0:
            for tid in all_teacher_ids:
                for day in DAYS:
                    day_slots_sorted = sorted([si for si in range(n_slots) if slot_day_of[si] == day],
                                              key=lambda si: slot_num_of[si])
                    if len(day_slots_sorted) < 3:
                        continue
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
                    n_day = len(day_slots_sorted)
                    for ji in range(n_day):
                        for ki in range(ji + 2, n_day):
                            for ii in range(ji + 1, ki):
                                sj, sk, sm = day_slots_sorted[ji], day_slots_sorted[ki], day_slots_sorted[ii]
                                gap_v = model.NewBoolVar(f"gap_{tid}_{day}_{sj}_{sm}_{sk}")
                                model.AddBoolAnd([teacher_at[sj], teacher_at[sk],
                                                  teacher_at[sm].Not()]).OnlyEnforceIf(gap_v)
                                model.AddBoolOr([teacher_at[sj].Not(), teacher_at[sk].Not(),
                                                 teacher_at[sm]]).OnlyEnforceIf(gap_v.Not())
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
    import threading

    n_bool_vars = len(x) + len(t)
    n_int_vars  = len(slot_var)
    _w = int(os.environ.get("SOLVER_WORKERS", "0"))
    n_workers = _w if _w > 0 else min(multiprocessing.cpu_count(), 16)
    max_mem   = int(os.environ.get("SOLVER_MAX_MEMORY_MB", 2048))

    logger.info(
        "Timetable %d: CP-SAT %d BoolVars + %d IntVars (AllDiff), limite=%ds, workers=%d, mem=%dMB",
        timetable_id, n_bool_vars, n_int_vars, max_time, n_workers, max_mem,
    )
    _log(db, tt, f"Modelo criado: {n_bool_vars} BoolVars + {n_int_vars} IntVars (AllDifferent). A resolver... (limite: {max_time}s, workers: {n_workers})")

    # ── Phase 1: find ANY feasible solution quickly ────────────────────────────
    # Strategy: PORTFOLIO_WITH_QUICK_RESTART with no LP overhead (linearization=0).
    # Allocate up to 40% of total time (min 60s, max 300s) for feasibility.
    phase1_time = max(60, min(int(max_time * 0.4), 300))
    solver1 = cp_model.CpSolver()
    solver1.parameters.max_time_in_seconds = float(phase1_time)
    solver1.parameters.num_workers = n_workers
    solver1.parameters.max_memory_in_mb = max_mem
    solver1.parameters.search_branching = 6   # PORTFOLIO_WITH_QUICK_RESTART
    solver1.parameters.linearization_level = 0  # skip LP in feasibility phase — faster search
    solver1.parameters.symmetry_level = 2       # default

    # Temporarily remove objective to find feasibility fast
    has_objective = bool(penalty_terms)
    if has_objective:
        # Solve a copy — OR-Tools models are not easily cloned, so we use
        # a fresh solver on the same model with ClearObjective via assumptions trick.
        # Simplest: just solve with objective but PORTFOLIO_WITH_QUICK_RESTART strategy
        # which finds a feasible solution quickly then keeps improving.
        pass  # use model as-is; PORTFOLIO_WITH_QUICK_RESTART already handles this

    # Heartbeat thread
    heartbeat_stop = threading.Event()
    start_wall = datetime.utcnow()
    def _heartbeat():
        elapsed = 0
        while not heartbeat_stop.wait(60):
            elapsed += 60
            try:
                from app.database import SessionLocal as _SL
                from app.models.models import Timetable as _TT
                _db = _SL()
                _tt = _db.query(_TT).filter(_TT.id == timetable_id).first()
                if _tt:
                    _log(_db, _tt, f"A calcular... ({elapsed}s decorridos)")
                _db.close()
            except Exception:
                pass
    hb = threading.Thread(target=_heartbeat, daemon=True)
    hb.start()

    status = solver1.Solve(model)
    phase1_wall = solver1.WallTime()

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Phase 1 found a solution — collect it as hints for phase 2
        _log(db, tt, f"Fase 1: solução encontrada em {phase1_wall:.1f}s — a otimizar...")
        remaining = max_time - phase1_wall
        solver = solver1  # already has result; use for extraction below
        if remaining > 10 and has_objective and status != cp_model.OPTIMAL:
            # Phase 2: optimize from the feasible solution found in phase 1.
            # Provide warm-start hints for all decision vars (x, t, slot_var).
            hints = {}
            for k, v in x.items():
                hints[v] = solver1.Value(v)
            for k, v in t.items():
                hints[v] = solver1.Value(v)
            for k, v in slot_var.items():
                hints[v] = solver1.Value(v)
            for var, val in hints.items():
                model.AddHint(var, val)
            solver2 = cp_model.CpSolver()
            solver2.parameters.max_time_in_seconds = float(remaining)
            solver2.parameters.num_workers = n_workers
            solver2.parameters.max_memory_in_mb = max_mem
            # Quality-maximising parameters for phase 2:
            solver2.parameters.linearization_level = 2    # strong LP relaxation → tighter bounds
            solver2.parameters.symmetry_level = 4         # aggressive symmetry breaking
            solver2.parameters.repair_hint = True         # repair phase-1 solution first (fast warm-start)
            solver2.parameters.search_branching = 0       # AUTOMATIC — best for multi-phase optimization
            solver2.parameters.interleave_search = True   # diversify LNS workers
            solver2.parameters.min_num_lns_workers = max(2, n_workers // 4)
            status2 = solver2.Solve(model)
            if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solver = solver2
                status = status2
                _log(db, tt, f"Fase 2: {solver2.StatusName(status2)} em {solver2.WallTime():.1f}s adicionais (obj={solver2.ObjectiveValue():.0f})")
            else:
                _log(db, tt, f"Fase 2: sem melhoria ({solver2.StatusName(status2)}) — a usar solução da fase 1")
    else:
        # Phase 1 failed — try phase 2 with remaining time and AUTOMATIC strategy
        remaining = max_time - phase1_wall
        if remaining > 30:
            _log(db, tt, f"Fase 1 sem solução ({solver1.StatusName(status)}) em {phase1_wall:.1f}s — tentativa com estratégia alternativa ({remaining:.0f}s)...")
            solver2 = cp_model.CpSolver()
            solver2.parameters.max_time_in_seconds = float(remaining)
            solver2.parameters.num_workers = n_workers
            solver2.parameters.max_memory_in_mb = max_mem
            solver2.parameters.random_seed = 42
            solver2.parameters.linearization_level = 2
            solver2.parameters.symmetry_level = 4
            solver2.parameters.interleave_search = True
            status2 = solver2.Solve(model)
            if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solver = solver2
                status = status2
            else:
                solver = solver2
                status = status2
        else:
            solver = solver1

    heartbeat_stop.set()
    hb.join(timeout=2)

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

            if all_fixed:
                assigned_teacher = teacher_of.get((eid, occ))
            else:
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
        if _relaxed_retry and _relaxed_labels:
            relaxed_str = " + ".join(_relaxed_labels)
            tt.solver_status = f"⚠ RESTRIÇÕES REMOVIDAS: {relaxed_str}"
            _log(db, tt, (
                f"⚠ Horário gerado SEM {relaxed_str}. "
                "Para eliminar os furos, regenere com mais tempo de cálculo (recomendado: 1h+) "
                "ou ajuste a disponibilidade/carga dos professores."
            ))
        else:
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
                f"INFEASIBLE — modelo sem solução em {solver.WallTime():.1f}s. "
                "Causas mais comuns:\n"
                "  1. Disciplina com ≥6 h/semana + 'Máx. 1 tempo/dia' ativado — desative essa opção\n"
                "  2. 'Alunos entram no 1.º tempo' demasiado restrito — experimente desativar\n"
                "  3. 'Sem furos nos alunos' com carga horária elevada — experimente desativar\n"
                "  4. Professor com disponibilidade muito limitada\n"
                "Tente gerar com menos restrições ativas e adicione-as progressivamente."
            )
        else:
            hint = status_name
        tt.solver_status = hint
        logger.error("Timetable %d: %s", timetable_id, hint)

    tt.updated_at = datetime.utcnow()
    db.commit()

    # ── Phase 3: auto-retry with relaxed constraints ──────────────────────────
    # If both phases failed and this isn't already a relaxed retry, automatically
    # try again without the two hardest structural constraints. These are the most
    # common causes of UNKNOWN on large staff/few classes scenarios.
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE) and not _relaxed_retry:
        relaxed_labels = []
        retry_opts = {k: v for k, v in opts.items()}
        if retry_opts.get('students_start_slot_1', True):
            retry_opts['students_start_slot_1'] = False
            relaxed_labels.append("'Alunos entram no 1.º tempo'")
        if retry_opts.get('no_student_gaps', True):
            retry_opts['no_student_gaps'] = False
            relaxed_labels.append("'Sem furos nos alunos'")
        if relaxed_labels:
            # Give Phase 3 a generous budget: 50% of original time, capped at 30 min.
            # Minimum 5 min so even short runs get a real retry.
            phase3_time = max(300, min(int(max_time * 0.5), 1800))
            retry_opts['max_time_seconds'] = phase3_time
            retry_opts['_relaxed_retry'] = True
            retry_opts['_relaxed_labels'] = relaxed_labels
            retry_opts['_preserve_log'] = True
            _log(db, tt, (
                f"Sem solução em {max_time}s com todas as restrições — "
                f"a tentar automaticamente sem {' e '.join(relaxed_labels)} ({phase3_time}s)..."
            ))
            db.commit()
            _run_solver(db, timetable_id, retry_opts)
            return  # inner call handles saving results

    logger.info(f"Timetable {timetable_id} generation complete: {tt.solver_status}")
