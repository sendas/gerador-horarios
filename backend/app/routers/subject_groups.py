from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import SubjectGroup, SubjectGroupEntry
from app.schemas.schemas import (
    SubjectGroupCreate, SubjectGroupUpdate, SubjectGroupResponse,
    SubjectGroupEntryCreate, SubjectGroupEntryResponse
)

router = APIRouter(prefix="/subject-groups", tags=["subject_groups"])


@router.get("", response_model=List[SubjectGroupResponse])
def list_subject_groups(academic_year_id: int = None, db: Session = Depends(get_db)):
    q = db.query(SubjectGroup)
    if academic_year_id:
        q = q.filter(SubjectGroup.academic_year_id == academic_year_id)
    return q.all()


@router.post("", response_model=SubjectGroupResponse, status_code=201)
def create_subject_group(data: SubjectGroupCreate, db: Session = Depends(get_db)):
    obj = SubjectGroup(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{id}", response_model=SubjectGroupResponse)
def get_subject_group(id: int, db: Session = Depends(get_db)):
    obj = db.query(SubjectGroup).filter(SubjectGroup.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject group not found")
    return obj


@router.put("/{id}", response_model=SubjectGroupResponse)
def update_subject_group(id: int, data: SubjectGroupUpdate, db: Session = Depends(get_db)):
    obj = db.query(SubjectGroup).filter(SubjectGroup.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject group not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
def delete_subject_group(id: int, db: Session = Depends(get_db)):
    obj = db.query(SubjectGroup).filter(SubjectGroup.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject group not found")
    db.delete(obj)
    db.commit()


@router.post("/{id}/entries", response_model=SubjectGroupEntryResponse, status_code=201)
def add_entry(id: int, data: SubjectGroupEntryCreate, db: Session = Depends(get_db)):
    group = db.query(SubjectGroup).filter(SubjectGroup.id == id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Subject group not found")
    obj = SubjectGroupEntry(group_id=id, curriculum_entry_id=data.curriculum_entry_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}/entries/{entry_id}", status_code=204)
def remove_entry(id: int, entry_id: int, db: Session = Depends(get_db)):
    obj = db.query(SubjectGroupEntry).filter(
        SubjectGroupEntry.id == entry_id,
        SubjectGroupEntry.group_id == id
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(obj)
    db.commit()
