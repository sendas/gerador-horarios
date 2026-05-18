from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import NonTeachingType, NonTeachingAssignment
from app.schemas.schemas import (
    NonTeachingTypeCreate, NonTeachingTypeUpdate, NonTeachingTypeResponse,
    NonTeachingAssignmentCreate, NonTeachingAssignmentUpdate, NonTeachingAssignmentResponse
)

router = APIRouter(prefix="/non-teaching", tags=["non_teaching"])


# Types

@router.get("/types", response_model=List[NonTeachingTypeResponse])
def list_types(cluster_id: int = None, db: Session = Depends(get_db)):
    q = db.query(NonTeachingType)
    if cluster_id:
        q = q.filter(NonTeachingType.cluster_id == cluster_id)
    return q.all()


@router.post("/types", response_model=NonTeachingTypeResponse, status_code=201)
def create_type(data: NonTeachingTypeCreate, db: Session = Depends(get_db)):
    obj = NonTeachingType(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/types/{id}", response_model=NonTeachingTypeResponse)
def update_type(id: int, data: NonTeachingTypeUpdate, db: Session = Depends(get_db)):
    obj = db.query(NonTeachingType).filter(NonTeachingType.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Type not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/types/{id}", status_code=204)
def delete_type(id: int, db: Session = Depends(get_db)):
    obj = db.query(NonTeachingType).filter(NonTeachingType.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Type not found")
    db.delete(obj)
    db.commit()


# Assignments

@router.get("/assignments", response_model=List[NonTeachingAssignmentResponse])
def list_assignments(
    teacher_id: int = None,
    academic_year_id: int = None,
    db: Session = Depends(get_db)
):
    q = db.query(NonTeachingAssignment)
    if teacher_id:
        q = q.filter(NonTeachingAssignment.teacher_id == teacher_id)
    if academic_year_id:
        q = q.filter(NonTeachingAssignment.academic_year_id == academic_year_id)
    return q.all()


@router.post("/assignments", response_model=NonTeachingAssignmentResponse, status_code=201)
def create_assignment(data: NonTeachingAssignmentCreate, db: Session = Depends(get_db)):
    obj = NonTeachingAssignment(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/assignments/{id}", response_model=NonTeachingAssignmentResponse)
def update_assignment(id: int, data: NonTeachingAssignmentUpdate, db: Session = Depends(get_db)):
    obj = db.query(NonTeachingAssignment).filter(NonTeachingAssignment.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Assignment not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/assignments/{id}", status_code=204)
def delete_assignment(id: int, db: Session = Depends(get_db)):
    obj = db.query(NonTeachingAssignment).filter(NonTeachingAssignment.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(obj)
    db.commit()
