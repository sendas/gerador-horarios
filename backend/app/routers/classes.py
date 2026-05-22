from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import Class, CurriculumEntry, School, TeacherSubject
from app.schemas.schemas import (
    ClassCreate, ClassUpdate, ClassResponse,
    CurriculumEntryCreate, CurriculumEntryUpdate, CurriculumEntryResponse
)

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get("", response_model=List[ClassResponse])
def list_classes(school_id: int = None, academic_year_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Class)
    if school_id:
        q = q.filter(Class.school_id == school_id)
    if academic_year_id:
        q = q.filter(Class.academic_year_id == academic_year_id)
    return q.all()


@router.get("/curriculum-overview")
def curriculum_overview(cluster_id: int, academic_year_id: int, db: Session = Depends(get_db)):
    """All curriculum entries in a cluster/year with class, subject and assigned teacher."""
    schools = db.query(School).filter(School.cluster_id == cluster_id).all()
    school_map = {s.id: s for s in schools}
    school_ids = [s.id for s in schools]
    entries = (
        db.query(CurriculumEntry)
        .join(Class, CurriculumEntry.class_id == Class.id)
        .filter(Class.school_id.in_(school_ids), Class.academic_year_id == academic_year_id)
        .order_by(Class.year_level, Class.name)
        .all()
    )
    return [{
        "id": e.id,
        "class_id": e.class_id,
        "class_name": e.class_.name if e.class_ else "",
        "year_level": e.class_.year_level if e.class_ else 0,
        "school_id": e.class_.school_id if e.class_ else None,
        "school_name": school_map.get(e.class_.school_id, None).name if e.class_ and e.class_.school_id in school_map else "",
        "subject_id": e.subject_id,
        "subject_name": e.subject.name if e.subject else "",
        "hours_per_week": e.hours_per_week,
        "teacher_id": e.teacher_id,
        "teacher_name": e.teacher.name if e.teacher else None,
    } for e in entries]


@router.post("", response_model=ClassResponse, status_code=201)
def create_class(data: ClassCreate, db: Session = Depends(get_db)):
    obj = Class(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{id}", response_model=ClassResponse)
def get_class(id: int, db: Session = Depends(get_db)):
    obj = db.query(Class).filter(Class.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Class not found")
    return obj


@router.put("/{id}", response_model=ClassResponse)
def update_class(id: int, data: ClassUpdate, db: Session = Depends(get_db)):
    obj = db.query(Class).filter(Class.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Class not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
def delete_class(id: int, db: Session = Depends(get_db)):
    obj = db.query(Class).filter(Class.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Class not found")
    db.delete(obj)
    db.commit()


# Curriculum entries

@router.get("/{id}/curriculum")
def list_curriculum(id: int, db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.id == id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    entries = db.query(CurriculumEntry).filter(CurriculumEntry.class_id == id).all()
    return [{
        **CurriculumEntryResponse.model_validate(e).model_dump(),
        "teacher_name": e.teacher.name if e.teacher else None,
    } for e in entries]


@router.post("/{id}/curriculum", response_model=CurriculumEntryResponse, status_code=201)
def add_curriculum_entry(id: int, data: CurriculumEntryCreate, db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.id == id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    fields = data.model_dump(exclude={"class_id"}, exclude_none=False)
    obj = CurriculumEntry(**{**fields, "class_id": id})
    db.add(obj)
    db.commit()
    db.refresh(obj)
    # auto-link teacher → subject so the solver also picks it up
    if obj.teacher_id and obj.subject_id:
        if not db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == obj.teacher_id,
            TeacherSubject.subject_id == obj.subject_id,
        ).first():
            db.add(TeacherSubject(teacher_id=obj.teacher_id, subject_id=obj.subject_id))
            db.commit()
    return obj


@router.put("/curriculum/{entry_id}", response_model=CurriculumEntryResponse)
def update_curriculum_entry(entry_id: int, data: CurriculumEntryUpdate, db: Session = Depends(get_db)):
    obj = db.query(CurriculumEntry).filter(CurriculumEntry.id == entry_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Curriculum entry not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    # Auto-link teacher → subject so the solver fallback also works
    if data.teacher_id and obj.subject_id:
        if not db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == data.teacher_id,
            TeacherSubject.subject_id == obj.subject_id,
        ).first():
            db.add(TeacherSubject(teacher_id=data.teacher_id, subject_id=obj.subject_id))
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/curriculum/{entry_id}", status_code=204)
def delete_curriculum_entry(entry_id: int, db: Session = Depends(get_db)):
    obj = db.query(CurriculumEntry).filter(CurriculumEntry.id == entry_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Curriculum entry not found")
    db.delete(obj)
    db.commit()
