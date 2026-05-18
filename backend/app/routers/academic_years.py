from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import AcademicYear
from app.schemas.schemas import AcademicYearCreate, AcademicYearUpdate, AcademicYearResponse

router = APIRouter(prefix="/academic-years", tags=["academic_years"])


@router.get("", response_model=List[AcademicYearResponse])
def list_academic_years(cluster_id: int = None, db: Session = Depends(get_db)):
    q = db.query(AcademicYear)
    if cluster_id:
        q = q.filter(AcademicYear.cluster_id == cluster_id)
    return q.all()


@router.post("", response_model=AcademicYearResponse, status_code=201)
def create_academic_year(data: AcademicYearCreate, db: Session = Depends(get_db)):
    obj = AcademicYear(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{id}", response_model=AcademicYearResponse)
def get_academic_year(id: int, db: Session = Depends(get_db)):
    obj = db.query(AcademicYear).filter(AcademicYear.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Academic year not found")
    return obj


@router.put("/{id}", response_model=AcademicYearResponse)
def update_academic_year(id: int, data: AcademicYearUpdate, db: Session = Depends(get_db)):
    obj = db.query(AcademicYear).filter(AcademicYear.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Academic year not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{id}/activate", response_model=AcademicYearResponse)
def activate_academic_year(id: int, db: Session = Depends(get_db)):
    obj = db.query(AcademicYear).filter(AcademicYear.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Academic year not found")
    db.query(AcademicYear).filter(
        AcademicYear.cluster_id == obj.cluster_id
    ).update({"is_active": False})
    obj.is_active = True
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
def delete_academic_year(id: int, db: Session = Depends(get_db)):
    obj = db.query(AcademicYear).filter(AcademicYear.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Academic year not found")
    db.delete(obj)
    db.commit()
