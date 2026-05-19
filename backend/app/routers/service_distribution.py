from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import (
    Teacher, ScheduledLesson, CurriculumEntry, Class, Subject,
    NonTeachingAssignment, Timetable, AcademicYear, TeacherSchoolAssignment,
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
    teacher_ids_q = (
        db.query(TeacherSchoolAssignment.teacher_id)
        .filter(TeacherSchoolAssignment.academic_year_id == academic_year_id)
        .distinct()
    )
    teacher_ids = {row[0] for row in teacher_ids_q.all()}

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

        result.append({
            "id": teacher.id,
            "name": teacher.name,
            "teaching_component": teaching_component,
            "scheduled_hours": scheduled_hours,
            "non_teaching_hours": non_teaching_count,
            "total_service": total_service,
            "classes_taught": classes_taught,
        })

    return {"teachers": result, "timetables": timetables}
