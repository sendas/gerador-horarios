from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models.models import (
    Timetable, ScheduledLesson, CurriculumEntry, Teacher, Room,
    Class, TimeSlotConfig, SchedulingRules, TeacherSchoolAssignment, School
)
from app.schemas.schemas import (
    TimetableCreate, TimetableUpdate, TimetableResponse,
    TimetableDetail, ScheduledLessonDetail
)


class MoveLessonRequest(BaseModel):
    day_of_week: int
    slot_number: int
    force: bool = False


class GenerationOptions(BaseModel):
    year_levels: Optional[List[int]] = None  # None=all, [5,6]=2nd cycle, [7,8,9]=3rd cycle
    school_ids: Optional[List[int]] = None   # None=all schools
    class_ids: Optional[List[int]] = None    # None=all classes (overrides year_levels/school_ids if set)
    no_student_gaps: bool = True
    minimize_teacher_gaps: bool = True
    teacher_gap_weight: int = 10
    no_same_subject_twice_per_day: bool = True
    distribute_subjects_weight: int = 5
    max_time_seconds: int = 300
    students_start_slot_1: bool = True
    no_pe_after_lunch: bool = True
    lunch_after_slot: int = 4

router = APIRouter(prefix="/timetables", tags=["timetables"])


def build_lesson_detail(lesson: ScheduledLesson) -> dict:
    entry = lesson.curriculum_entry
    paired = entry.paired_entry if entry else None
    return {
        "id": lesson.id,
        "timetable_id": lesson.timetable_id,
        "day_of_week": lesson.day_of_week,
        "slot_number": lesson.slot_number,
        "curriculum_entry_id": lesson.curriculum_entry_id,
        "teacher_id": lesson.teacher_id,
        "room_id": lesson.room_id,
        "semester": lesson.semester,
        "is_semestral": bool(entry.is_semestral) if entry else False,
        "paired_entry_id": entry.paired_entry_id if entry else None,
        "subject_name": entry.subject.name if entry and entry.subject else None,
        "subject_color": entry.subject.color if entry and entry.subject else None,
        "class_name": entry.class_.name if entry and entry.class_ else None,
        "teacher_name": lesson.teacher.name if lesson.teacher else None,
        "room_name": lesson.room.name if lesson.room else None,
        "paired_subject_name": paired.subject.name if paired and paired.subject else None,
        "paired_subject_color": paired.subject.color if paired and paired.subject else None,
    }


@router.get("/preflight-check")
def preflight_check(academic_year_id: int, cluster_id: int, db: Session = Depends(get_db)):
    errors, warnings, info = [], [], []

    # 1. Time slots
    slots = db.query(TimeSlotConfig).filter(TimeSlotConfig.academic_year_id == academic_year_id).count()
    if slots == 0:
        errors.append({"message": "Sem tempos letivos configurados para este ano letivo.", "fix": "/time-slots"})
    else:
        info.append({"message": f"{slots} tempos letivos configurados."})

    # 2. Scheduling rules
    rules = db.query(SchedulingRules).filter(
        SchedulingRules.cluster_id == cluster_id,
        SchedulingRules.academic_year_id == academic_year_id
    ).first()
    if not rules:
        warnings.append({"message": "Sem regras de horário definidas — serão usados valores por omissão.", "fix": "/scheduling-rules"})

    # 3. Schools and classes in cluster
    school_ids = [s.id for s in db.query(School).filter(School.cluster_id == cluster_id).all()]
    if not school_ids:
        errors.append({"message": "Sem escolas no agrupamento.", "fix": "/schools"})
        return {"errors": errors, "warnings": warnings, "info": info, "can_generate": False}

    classes = db.query(Class).filter(
        Class.school_id.in_(school_ids),
        Class.academic_year_id == academic_year_id
    ).all()
    class_ids = [c.id for c in classes]
    if not class_ids:
        errors.append({"message": "Sem turmas para este ano letivo.", "fix": "/classes"})
        return {"errors": errors, "warnings": warnings, "info": info, "can_generate": False}
    info.append({"message": f"{len(classes)} turmas encontradas."})

    # 4. Curriculum entries
    all_entries = db.query(CurriculumEntry).filter(CurriculumEntry.class_id.in_(class_ids)).all()
    if not all_entries:
        errors.append({"message": "Sem entradas curriculares para estas turmas.", "fix": "/import-curriculum"})
        return {"errors": errors, "warnings": warnings, "info": info, "can_generate": False}
    info.append({"message": f"{len(all_entries)} entradas curriculares no total."})

    # 5. Entries without teacher
    no_teacher = [e for e in all_entries if not e.teacher_id]
    with_teacher = [e for e in all_entries if e.teacher_id]
    if not with_teacher:
        errors.append({
            "message": "Nenhuma entrada tem professor atribuído — impossível gerar horários.",
            "fix": "/teacher-assignment",
            "items": [f"{e.class_.name} · {e.subject.name if e.subject else '?'}" for e in no_teacher[:20]]
        })
    elif no_teacher:
        warnings.append({
            "message": f"{len(no_teacher)} entrada(s) sem professor — serão excluídas da geração.",
            "fix": "/teacher-assignment",
            "items": [f"{e.class_.name} · {e.subject.name if e.subject else '?'}" for e in no_teacher[:20]]
        })
    else:
        info.append({"message": f"Todos os {len(with_teacher)} entradas têm professor atribuído."})

    # 6. Teachers without school assignment
    teacher_ids = list({e.teacher_id for e in with_teacher})
    teachers_no_school = []
    for tid in teacher_ids:
        has_school = db.query(TeacherSchoolAssignment).filter(
            TeacherSchoolAssignment.teacher_id == tid,
            TeacherSchoolAssignment.academic_year_id == academic_year_id
        ).first()
        if not has_school:
            t = db.query(Teacher).filter(Teacher.id == tid).first()
            if t:
                teachers_no_school.append(t.name)
    if teachers_no_school:
        warnings.append({
            "message": f"{len(teachers_no_school)} professor(es) sem escola atribuída — podem causar problemas no solver.",
            "fix": "/teachers",
            "items": teachers_no_school[:20]
        })

    can_generate = len(errors) == 0

    # Per-year-level viability summary
    from collections import defaultdict
    yl_data: dict = defaultdict(lambda: {"total_classes": 0, "total_entries": 0, "entries_with_teacher": 0})
    class_by_id = {c.id: c for c in classes}
    for c in classes:
        yl_data[c.year_level]["total_classes"] += 1
    for entry in all_entries:
        cls = class_by_id.get(entry.class_id)
        if cls:
            yl_data[cls.year_level]["total_entries"] += 1
            if entry.teacher_id:
                yl_data[cls.year_level]["entries_with_teacher"] += 1

    year_level_summary = [
        {
            "year_level": yl,
            "total_classes": d["total_classes"],
            "total_entries": d["total_entries"],
            "entries_with_teacher": d["entries_with_teacher"],
            "viable": d["entries_with_teacher"] > 0,
        }
        for yl, d in sorted(yl_data.items())
    ]

    return {"errors": errors, "warnings": warnings, "info": info, "can_generate": can_generate, "year_level_summary": year_level_summary}


@router.get("", response_model=List[TimetableResponse])
def list_timetables(academic_year_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Timetable)
    if academic_year_id:
        q = q.filter(Timetable.academic_year_id == academic_year_id)
    return q.all()


@router.post("", response_model=TimetableResponse, status_code=201)
def create_timetable(data: TimetableCreate, db: Session = Depends(get_db)):
    obj = Timetable(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{id}", response_model=TimetableDetail)
def get_timetable(id: int, db: Session = Depends(get_db)):
    obj = db.query(Timetable).filter(Timetable.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Timetable not found")
    lessons = [build_lesson_detail(l) for l in obj.scheduled_lessons]
    return {
        "id": obj.id,
        "academic_year_id": obj.academic_year_id,
        "name": obj.name,
        "status": obj.status,
        "solver_status": obj.solver_status,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
        "lessons": lessons,
    }


@router.put("/{id}", response_model=TimetableResponse)
def update_timetable(id: int, data: TimetableUpdate, db: Session = Depends(get_db)):
    obj = db.query(Timetable).filter(Timetable.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Timetable not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
def delete_timetable(id: int, db: Session = Depends(get_db)):
    obj = db.query(Timetable).filter(Timetable.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Timetable not found")
    db.delete(obj)
    db.commit()


@router.post("/{id}/generate")
def generate_timetable(
    id: int,
    background_tasks: BackgroundTasks,
    options: GenerationOptions = None,
    db: Session = Depends(get_db)
):
    obj = db.query(Timetable).filter(Timetable.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Timetable not found")
    if obj.status == "generating":
        raise HTTPException(status_code=400, detail="Timetable is already being generated")
    obj.status = "generating"
    obj.updated_at = datetime.utcnow()
    db.commit()

    options = options or GenerationOptions()
    from app.scheduler.engine import generate_timetable as run_solver
    background_tasks.add_task(run_solver, id, options.model_dump())
    return {"message": "Generation started", "timetable_id": id}


@router.get("/{id}/by-teacher/{teacher_id}")
def get_by_teacher(id: int, teacher_id: int, db: Session = Depends(get_db)):
    obj = db.query(Timetable).filter(Timetable.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Timetable not found")
    lessons = db.query(ScheduledLesson).filter(
        ScheduledLesson.timetable_id == id,
        ScheduledLesson.teacher_id == teacher_id
    ).all()
    return [build_lesson_detail(l) for l in lessons]


@router.get("/{id}/by-class/{class_id}")
def get_by_class(id: int, class_id: int, db: Session = Depends(get_db)):
    obj = db.query(Timetable).filter(Timetable.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Timetable not found")
    lessons = (
        db.query(ScheduledLesson)
        .join(CurriculumEntry, ScheduledLesson.curriculum_entry_id == CurriculumEntry.id)
        .filter(
            ScheduledLesson.timetable_id == id,
            CurriculumEntry.class_id == class_id
        ).all()
    )
    return [build_lesson_detail(l) for l in lessons]


@router.get("/{id}/by-room/{room_id}")
def get_by_room(id: int, room_id: int, db: Session = Depends(get_db)):
    obj = db.query(Timetable).filter(Timetable.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Timetable not found")
    lessons = db.query(ScheduledLesson).filter(
        ScheduledLesson.timetable_id == id,
        ScheduledLesson.room_id == room_id
    ).all()
    return [build_lesson_detail(l) for l in lessons]


@router.patch("/{id}/lessons/{lesson_id}")
def move_lesson(
    id: int,
    lesson_id: int,
    body: MoveLessonRequest,
    db: Session = Depends(get_db),
):
    """Move a scheduled lesson to a different day/slot, with conflict detection."""
    lesson = db.query(ScheduledLesson).filter(
        ScheduledLesson.id == lesson_id,
        ScheduledLesson.timetable_id == id,
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Aula não encontrada")

    if lesson.day_of_week == body.day_of_week and lesson.slot_number == body.slot_number:
        return {"lesson": build_lesson_detail(lesson), "conflicts": []}

    conflicts = []
    entry = lesson.curriculum_entry

    # 1. Class conflict: another lesson for the same class at the target slot
    if entry:
        class_conflict = (
            db.query(ScheduledLesson)
            .join(CurriculumEntry, ScheduledLesson.curriculum_entry_id == CurriculumEntry.id)
            .filter(
                ScheduledLesson.timetable_id == id,
                ScheduledLesson.id != lesson_id,
                ScheduledLesson.day_of_week == body.day_of_week,
                ScheduledLesson.slot_number == body.slot_number,
                CurriculumEntry.class_id == entry.class_id,
            )
            .first()
        )
        if class_conflict:
            cc = class_conflict.curriculum_entry
            conflicts.append({
                "type": "class",
                "lesson_id": class_conflict.id,
                "subject_name": cc.subject.name if cc and cc.subject else "?",
                "class_name": cc.class_.name if cc and cc.class_ else "?",
            })

    # 2. Teacher conflict: another lesson for the same teacher at the target slot
    if lesson.teacher_id:
        teacher_conflict = db.query(ScheduledLesson).filter(
            ScheduledLesson.timetable_id == id,
            ScheduledLesson.id != lesson_id,
            ScheduledLesson.day_of_week == body.day_of_week,
            ScheduledLesson.slot_number == body.slot_number,
            ScheduledLesson.teacher_id == lesson.teacher_id,
        ).first()
        if teacher_conflict:
            tc = teacher_conflict.curriculum_entry
            conflicts.append({
                "type": "teacher",
                "lesson_id": teacher_conflict.id,
                "subject_name": tc.subject.name if tc and tc.subject else "?",
                "class_name": tc.class_.name if tc and tc.class_ else "?",
                "teacher_name": lesson.teacher.name if lesson.teacher else "?",
            })

    if conflicts and not body.force:
        raise HTTPException(
            status_code=409,
            detail={"message": "Conflitos detectados", "conflicts": conflicts},
        )

    lesson.day_of_week = body.day_of_week
    lesson.slot_number = body.slot_number
    db.commit()
    db.refresh(lesson)
    return {"lesson": build_lesson_detail(lesson), "conflicts": conflicts}
