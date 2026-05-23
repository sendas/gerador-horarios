from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import (
    Teacher, ScheduledLesson, CurriculumEntry, Class, Subject,
    NonTeachingAssignment, Timetable, AcademicYear, TeacherSchoolAssignment, School,
)

router = APIRouter(prefix="/service-distribution", tags=["service_distribution"])


@router.get("")
def get_service_distribution(
    academic_year_id: int,
    timetable_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    # Resolve the cluster_id from the academic year so we only surface teachers
    # that belong to the same cluster (mirrors the pattern used by other routers).
    year = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    cluster_id = year.cluster_id if year else None

    # All timetables for this academic year (for the selector on the frontend)
    timetables_q = db.query(Timetable).filter(
        Timetable.academic_year_id == academic_year_id
    ).order_by(Timetable.name)
    timetables = [{"id": t.id, "name": t.name} for t in timetables_q.all()]

    # Teachers assigned to this academic year via TeacherSchoolAssignment
    assignments_q = (
        db.query(TeacherSchoolAssignment)
        .filter(TeacherSchoolAssignment.academic_year_id == academic_year_id)
        .all()
    )
    teacher_ids = {a.teacher_id for a in assignments_q}
    # Map teacher_id -> primary school (name + id)
    primary_school_map: dict = {}
    for a in assignments_q:
        if a.is_primary or a.teacher_id not in primary_school_map:
            school = db.query(School).filter(School.id == a.school_id).first()
            primary_school_map[a.teacher_id] = {
                "id": a.school_id,
                "name": school.name if school else None,
                "is_primary": bool(a.is_primary),
            }

    # Build unique school list for the filter
    school_ids_seen: set = set()
    schools_list = []
    for info in primary_school_map.values():
        if info["id"] not in school_ids_seen:
            school_ids_seen.add(info["id"])
            schools_list.append({"id": info["id"], "name": info["name"]})
    schools_list.sort(key=lambda s: s["name"] or "")

    # Fallback: all teachers in the cluster when no school assignments exist yet
    if not teacher_ids and cluster_id:
        all_teachers = db.query(Teacher).filter(Teacher.cluster_id == cluster_id).all()
        teacher_ids = {t.id for t in all_teachers}

    teachers_q = (
        db.query(Teacher)
        .filter(Teacher.id.in_(teacher_ids))
        .order_by(Teacher.name)
    )
    teachers = teachers_q.all()

    result = []
    for teacher in teachers:
        # ── Scheduled lessons ────────────────────────────────────────────────
        if timetable_id is not None:
            lessons = (
                db.query(ScheduledLesson)
                .filter(
                    ScheduledLesson.timetable_id == timetable_id,
                    ScheduledLesson.teacher_id == teacher.id,
                )
                .all()
            )
        else:
            lessons = []

        scheduled_hours = len(lessons)

        # ── Classes taught ────────────────────────────────────────────────────
        # Group by (class_id, subject_id) via CurriculumEntry; keep first
        # hours_per_week found for each combination.
        classes_taught_map: dict = {}  # (class_id, subject_id) -> dict
        for lesson in lessons:
            entry: Optional[CurriculumEntry] = lesson.curriculum_entry
            if entry is None:
                continue
            key = (entry.class_id, entry.subject_id)
            if key not in classes_taught_map:
                cls: Optional[Class] = entry.class_
                subj: Optional[Subject] = entry.subject
                classes_taught_map[key] = {
                    "class_name": cls.name if cls else "—",
                    "subject_name": subj.name if subj else "—",
                    "hours_per_week": entry.hours_per_week,
                }

        classes_taught = sorted(
            classes_taught_map.values(),
            key=lambda x: (x["class_name"], x["subject_name"]),
        )

        # ── Non-teaching assignments ──────────────────────────────────────────
        non_teaching_count = (
            db.query(NonTeachingAssignment)
            .filter(
                NonTeachingAssignment.teacher_id == teacher.id,
                NonTeachingAssignment.academic_year_id == academic_year_id,
            )
            .count()
        )

        # ── teaching_component — use the column when it exists, else None ────
        teaching_component = getattr(teacher, "teaching_component", None)

        total_service = scheduled_hours + non_teaching_count

        school_info = primary_school_map.get(teacher.id, {})
        result.append({
            "id": teacher.id,
            "name": teacher.name,
            "teaching_component": teaching_component,
            "scheduled_hours": scheduled_hours,
            "non_teaching_hours": non_teaching_count,
            "total_service": total_service,
            "classes_taught": classes_taught,
            "primary_school_id": school_info.get("id"),
            "primary_school_name": school_info.get("name"),
        })

    return {"teachers": result, "timetables": timetables, "schools": schools_list}
