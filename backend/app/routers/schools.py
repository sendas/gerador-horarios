from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import (
    School, Class, CurriculumEntry, ScheduledLesson, SubjectGroupEntry,
    TimetableLock, Room, TeacherSchoolAssignment, TimeSlotConfig,
    NonTeachingAssignment,
)
from app.schemas.schemas import SchoolCreate, SchoolUpdate, SchoolResponse

router = APIRouter(prefix="/schools", tags=["schools"])


@router.get("", response_model=List[SchoolResponse])
def list_schools(cluster_id: int = None, db: Session = Depends(get_db)):
    q = db.query(School)
    if cluster_id:
        q = q.filter(School.cluster_id == cluster_id)
    return q.all()


@router.post("", response_model=SchoolResponse, status_code=201)
def create_school(data: SchoolCreate, db: Session = Depends(get_db)):
    existing = db.query(School).filter(School.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="School with this code already exists")
    obj = School(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{id}", response_model=SchoolResponse)
def get_school(id: int, db: Session = Depends(get_db)):
    obj = db.query(School).filter(School.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="School not found")
    return obj


@router.put("/{id}", response_model=SchoolResponse)
def update_school(id: int, data: SchoolUpdate, db: Session = Depends(get_db)):
    obj = db.query(School).filter(School.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="School not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
def delete_school(id: int, db: Session = Depends(get_db)):
    obj = db.query(School).filter(School.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="School not found")
    class_ids = [
        row.id for row in db.query(Class.id)
        .filter(Class.school_id == id)
        .all()
    ]
    if class_ids:
        entry_ids = [
            row.id for row in db.query(CurriculumEntry.id)
            .filter(CurriculumEntry.class_id.in_(class_ids))
            .all()
        ]
        if entry_ids:
            db.query(ScheduledLesson).filter(ScheduledLesson.curriculum_entry_id.in_(entry_ids)).delete(synchronize_session=False)
            db.query(SubjectGroupEntry).filter(SubjectGroupEntry.curriculum_entry_id.in_(entry_ids)).delete(synchronize_session=False)
            db.query(CurriculumEntry).filter(CurriculumEntry.paired_entry_id.in_(entry_ids)).update(
                {"paired_entry_id": None},
                synchronize_session=False,
            )
            db.query(CurriculumEntry).filter(CurriculumEntry.id.in_(entry_ids)).delete(synchronize_session=False)
        db.query(TimetableLock).filter(
            TimetableLock.lock_type == "class",
            TimetableLock.entity_id.in_(class_ids),
        ).delete(synchronize_session=False)
        db.query(Class).filter(Class.id.in_(class_ids)).delete(synchronize_session=False)

    room_ids = [
        row.id for row in db.query(Room.id)
        .filter(Room.school_id == id)
        .all()
    ]
    if room_ids:
        db.query(ScheduledLesson).filter(ScheduledLesson.room_id.in_(room_ids)).update(
            {"room_id": None},
            synchronize_session=False,
        )
        db.query(Room).filter(Room.id.in_(room_ids)).delete(synchronize_session=False)

    db.query(TeacherSchoolAssignment).filter(TeacherSchoolAssignment.school_id == id).delete(synchronize_session=False)
    db.query(TimeSlotConfig).filter(TimeSlotConfig.school_id == id).delete(synchronize_session=False)
    db.query(NonTeachingAssignment).filter(NonTeachingAssignment.school_id == id).update(
        {"school_id": None},
        synchronize_session=False,
    )
    db.delete(obj)
    db.commit()
