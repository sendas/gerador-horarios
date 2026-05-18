from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import Room
from app.schemas.schemas import RoomCreate, RoomUpdate, RoomResponse

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=List[RoomResponse])
def list_rooms(school_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Room)
    if school_id:
        q = q.filter(Room.school_id == school_id)
    return q.all()


@router.post("", response_model=RoomResponse, status_code=201)
def create_room(data: RoomCreate, db: Session = Depends(get_db)):
    obj = Room(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{id}", response_model=RoomResponse)
def get_room(id: int, db: Session = Depends(get_db)):
    obj = db.query(Room).filter(Room.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Room not found")
    return obj


@router.put("/{id}", response_model=RoomResponse)
def update_room(id: int, data: RoomUpdate, db: Session = Depends(get_db)):
    obj = db.query(Room).filter(Room.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Room not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
def delete_room(id: int, db: Session = Depends(get_db)):
    obj = db.query(Room).filter(Room.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Room not found")
    db.delete(obj)
    db.commit()
