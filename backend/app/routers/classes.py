from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import Class, CurriculumEntry
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

@router.get("/{id}/curriculum", response_model=List[CurriculumEntryResponse])
def list_curriculum(id: int, db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.id == id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    return db.query(CurriculumEntry).filter(CurriculumEntry.class_id == id).all()


@router.post("/{id}/curriculum", response_model=CurriculumEntryResponse, status_code=201)
def add_curriculum_entry(id: int, data: CurriculumEntryCreate, db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.id == id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    obj = CurriculumEntry(**{**data.model_dump(), "class_id": id})
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/curriculum/{entry_id}", response_model=CurriculumEntryResponse)
def update_curriculum_entry(entry_id: int, data: CurriculumEntryUpdate, db: Session = Depends(get_db)):
    obj = db.query(CurriculumEntry).filter(CurriculumEntry.id == entry_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Curriculum entry not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
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
