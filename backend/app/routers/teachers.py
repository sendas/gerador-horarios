from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import (
    Teacher, TeacherSchoolAssignment, TeacherSubject, TeacherAvailability,
    CurriculumEntry, Class, Subject
)
from app.schemas.schemas import (
    TeacherCreate, TeacherUpdate, TeacherResponse,
    TeacherSchoolAssignmentCreate, TeacherSchoolAssignmentResponse,
    TeacherAvailabilityCreate, TeacherAvailabilityResponse, TeacherAvailabilityBulk
)

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("", response_model=List[TeacherResponse])
def list_teachers(cluster_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Teacher)
    if cluster_id:
        q = q.filter(Teacher.cluster_id == cluster_id)
    teachers = q.all()
    result = []
    for t in teachers:
        r = TeacherResponse.model_validate(t)
        r.subject_names = sorted(ts.subject.name for ts in t.teacher_subjects if ts.subject)
        r.school_ids = list({sa.school_id for sa in t.school_assignments})
        result.append(r)
    return result


@router.post("", response_model=TeacherResponse, status_code=201)
def create_teacher(data: TeacherCreate, db: Session = Depends(get_db)):
    obj = Teacher(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{id}", response_model=TeacherResponse)
def get_teacher(id: int, db: Session = Depends(get_db)):
    obj = db.query(Teacher).filter(Teacher.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return obj


@router.put("/{id}", response_model=TeacherResponse)
def update_teacher(id: int, data: TeacherUpdate, db: Session = Depends(get_db)):
    obj = db.query(Teacher).filter(Teacher.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Teacher not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
def delete_teacher(id: int, db: Session = Depends(get_db)):
    obj = db.query(Teacher).filter(Teacher.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Teacher not found")
    db.delete(obj)
    db.commit()


@router.get("/{id}/curriculum")
def list_teacher_curriculum(id: int, academic_year_id: int = None, db: Session = Depends(get_db)):
    """Return all curriculum entries assigned to this teacher, with class/subject names."""
    q = db.query(CurriculumEntry).filter(CurriculumEntry.teacher_id == id)
    if academic_year_id:
        q = q.join(Class).filter(Class.academic_year_id == academic_year_id)
    entries = q.all()
    return [{
        "id": e.id,
        "class_id": e.class_id,
        "class_name": e.class_.name if e.class_ else "",
        "year_level": e.class_.year_level if e.class_ else 0,
        "subject_id": e.subject_id,
        "subject_name": e.subject.name if e.subject else "",
        "hours_per_week": e.hours_per_week,
        "teacher_id": e.teacher_id,
    } for e in entries]


# School assignments

@router.get("/{id}/school-assignments", response_model=List[TeacherSchoolAssignmentResponse])
def list_school_assignments(id: int, db: Session = Depends(get_db)):
    return db.query(TeacherSchoolAssignment).filter(TeacherSchoolAssignment.teacher_id == id).all()


@router.post("/{id}/school-assignments", response_model=TeacherSchoolAssignmentResponse, status_code=201)
def add_school_assignment(id: int, data: TeacherSchoolAssignmentCreate, db: Session = Depends(get_db)):
    obj = TeacherSchoolAssignment(**{**data.model_dump(), "teacher_id": id})
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/school-assignments/{assignment_id}", status_code=204)
def delete_school_assignment(assignment_id: int, db: Session = Depends(get_db)):
    obj = db.query(TeacherSchoolAssignment).filter(TeacherSchoolAssignment.id == assignment_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(obj)
    db.commit()


# Subject assignments

@router.get("/{id}/subjects")
def list_teacher_subjects(id: int, db: Session = Depends(get_db)):
    rows = db.query(TeacherSubject).filter(TeacherSubject.teacher_id == id).all()
    return [{"id": r.id, "teacher_id": r.teacher_id, "subject_id": r.subject_id} for r in rows]


@router.post("/{id}/subjects/{subject_id}", status_code=201)
def add_teacher_subject(id: int, subject_id: int, db: Session = Depends(get_db)):
    existing = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == id,
        TeacherSubject.subject_id == subject_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Assignment already exists")
    obj = TeacherSubject(teacher_id=id, subject_id=subject_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"id": obj.id, "teacher_id": obj.teacher_id, "subject_id": obj.subject_id}


@router.delete("/{id}/subjects/{subject_id}", status_code=204)
def remove_teacher_subject(id: int, subject_id: int, db: Session = Depends(get_db)):
    obj = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == id,
        TeacherSubject.subject_id == subject_id
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(obj)
    db.commit()


# Availability

@router.get("/{id}/availability", response_model=List[TeacherAvailabilityResponse])
def get_availability(id: int, academic_year_id: int = None, db: Session = Depends(get_db)):
    q = db.query(TeacherAvailability).filter(TeacherAvailability.teacher_id == id)
    if academic_year_id:
        q = q.filter(TeacherAvailability.academic_year_id == academic_year_id)
    return q.all()


@router.post("/{id}/availability/bulk", response_model=List[TeacherAvailabilityResponse])
def set_availability_bulk(id: int, data: TeacherAvailabilityBulk, db: Session = Depends(get_db)):
    db.query(TeacherAvailability).filter(
        TeacherAvailability.teacher_id == id,
        TeacherAvailability.academic_year_id == data.academic_year_id
    ).delete()
    objs = [
        TeacherAvailability(**{**a.model_dump(), "teacher_id": id})
        for a in data.availabilities
    ]
    db.add_all(objs)
    db.commit()
    for obj in objs:
        db.refresh(obj)
    return objs
