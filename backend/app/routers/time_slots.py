from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import TimeSlotConfig
from app.schemas.schemas import TimeSlotConfigCreate, TimeSlotConfigUpdate, TimeSlotConfigResponse

router = APIRouter(prefix="/time-slots", tags=["time_slots"])


@router.get("", response_model=List[TimeSlotConfigResponse])
def list_time_slots(
    academic_year_id: int = None,
    school_id: int = None,
    db: Session = Depends(get_db)
):
    q = db.query(TimeSlotConfig)
    if academic_year_id:
        q = q.filter(TimeSlotConfig.academic_year_id == academic_year_id)
    if school_id is not None:
        q = q.filter(TimeSlotConfig.school_id == school_id)
    return q.order_by(TimeSlotConfig.day_of_week, TimeSlotConfig.slot_number).all()


@router.post("", response_model=TimeSlotConfigResponse, status_code=201)
def create_time_slot(data: TimeSlotConfigCreate, db: Session = Depends(get_db)):
    obj = TimeSlotConfig(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/bulk", response_model=List[TimeSlotConfigResponse], status_code=201)
def create_bulk_time_slots(data: List[TimeSlotConfigCreate], db: Session = Depends(get_db)):
    objs = [TimeSlotConfig(**item.model_dump()) for item in data]
    db.add_all(objs)
    db.commit()
    for obj in objs:
        db.refresh(obj)
    return objs


@router.get("/{id}", response_model=TimeSlotConfigResponse)
def get_time_slot(id: int, db: Session = Depends(get_db)):
    obj = db.query(TimeSlotConfig).filter(TimeSlotConfig.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Time slot not found")
    return obj


@router.put("/{id}", response_model=TimeSlotConfigResponse)
def update_time_slot(id: int, data: TimeSlotConfigUpdate, db: Session = Depends(get_db)):
    obj = db.query(TimeSlotConfig).filter(TimeSlotConfig.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Time slot not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
def delete_time_slot(id: int, db: Session = Depends(get_db)):
    obj = db.query(TimeSlotConfig).filter(TimeSlotConfig.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Time slot not found")
    db.delete(obj)
    db.commit()
