from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import Subject
from app.schemas.schemas import SubjectCreate, SubjectUpdate, SubjectResponse

router = APIRouter(prefix="/subjects", tags=["subjects"])


def _subject_dict(obj: Subject) -> dict:
    d = {
        "id": obj.id,
        "cluster_id": obj.cluster_id,
        "name": obj.name,
        "code": obj.code,
        "color": obj.color,
        "weekly_structure": obj.weekly_structure,
        "regime": obj.regime,
        "default_semester": obj.default_semester,
        "paired_subject_id": obj.paired_subject_id,
        "paired_subject_name": obj.paired_subject.name if obj.paired_subject else None,
        "is_physical_education": obj.is_physical_education,
        "can_exempt_articulado": obj.can_exempt_articulado,
    }
    return d


@router.get("")
def list_subjects(cluster_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Subject)
    if cluster_id:
        q = q.filter(Subject.cluster_id == cluster_id)
    return [_subject_dict(s) for s in q.all()]


@router.post("", status_code=201)
def create_subject(data: SubjectCreate, db: Session = Depends(get_db)):
    obj = Subject(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _subject_dict(obj)


@router.get("/{id}")
def get_subject(id: int, db: Session = Depends(get_db)):
    obj = db.query(Subject).filter(Subject.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject not found")
    return _subject_dict(obj)


@router.put("/{id}")
def update_subject(id: int, data: SubjectUpdate, db: Session = Depends(get_db)):
    obj = db.query(Subject).filter(Subject.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return _subject_dict(obj)


@router.delete("/{id}", status_code=204)
def delete_subject(id: int, db: Session = Depends(get_db)):
    obj = db.query(Subject).filter(Subject.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.delete(obj)
    db.commit()
