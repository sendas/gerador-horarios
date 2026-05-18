from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models.models import Timetable, ScheduledLesson, CurriculumEntry, Teacher, Room
from app.schemas.schemas import (
    TimetableCreate, TimetableUpdate, TimetableResponse,
    TimetableDetail, ScheduledLessonDetail
)


class GenerationOptions(BaseModel):
    year_levels: Optional[List[int]] = None  # None=all, [5,6]=2nd cycle, [7,8,9]=3rd cycle
    no_student_gaps: bool = True
    minimize_teacher_gaps: bool = True
    teacher_gap_weight: int = 10
    no_same_subject_twice_per_day: bool = True
    distribute_subjects_weight: int = 5
    max_time_seconds: int = 120

router = APIRouter(prefix="/timetables", tags=["timetables"])


def build_lesson_detail(lesson: ScheduledLesson) -> dict:
    entry = lesson.curriculum_entry
    return {
        "id": lesson.id,
        "timetable_id": lesson.timetable_id,
        "day_of_week": lesson.day_of_week,
        "slot_number": lesson.slot_number,
        "curriculum_entry_id": lesson.curriculum_entry_id,
        "teacher_id": lesson.teacher_id,
        "room_id": lesson.room_id,
        "subject_name": entry.subject.name if entry and entry.subject else None,
        "subject_color": entry.subject.color if entry and entry.subject else None,
        "class_name": entry.class_.name if entry and entry.class_ else None,
        "teacher_name": lesson.teacher.name if lesson.teacher else None,
        "room_name": lesson.room.name if lesson.room else None,
    }


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
