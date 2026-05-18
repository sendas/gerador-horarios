from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import Subject
from app.schemas.schemas import SubjectCreate, SubjectUpdate, SubjectResponse

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=List[SubjectResponse])
def list_subjects(cluster_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Subject)
    if cluster_id:
        q = q.filter(Subject.cluster_id == cluster_id)
    return q.all()


@router.post("", response_model=SubjectResponse, status_code=201)
def create_subject(data: SubjectCreate, db: Session = Depends(get_db)):
    obj = Subject(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{id}", response_model=SubjectResponse)
def get_subject(id: int, db: Session = Depends(get_db)):
    obj = db.query(Subject).filter(Subject.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject not found")
    return obj


@router.put("/{id}", response_model=SubjectResponse)
def update_subject(id: int, data: SubjectUpdate, db: Session = Depends(get_db)):
    obj = db.query(Subject).filter(Subject.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
def delete_subject(id: int, db: Session = Depends(get_db)):
    obj = db.query(Subject).filter(Subject.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.delete(obj)
    db.commit()
