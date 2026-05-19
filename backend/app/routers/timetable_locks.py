from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.models import TimetableLock, Timetable

router = APIRouter(prefix="/timetables", tags=["timetable_locks"])


class LockCreate(BaseModel):
    lock_type: str   # 'teacher' | 'class'
    entity_id: int


class LockResponse(BaseModel):
    id: int
    timetable_id: int
    lock_type: str
    entity_id: int

    class Config:
        from_attributes = True


@router.get("/{timetable_id}/locks", response_model=list[LockResponse])
def get_locks(timetable_id: int, db: Session = Depends(get_db)):
    return db.query(TimetableLock).filter(TimetableLock.timetable_id == timetable_id).all()


@router.post("/{timetable_id}/locks", response_model=LockResponse)
def add_lock(timetable_id: int, body: LockCreate, db: Session = Depends(get_db)):
    tt = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail="Timetable not found")
    if body.lock_type not in ("teacher", "class"):
        raise HTTPException(status_code=422, detail="lock_type must be 'teacher' or 'class'")
    existing = db.query(TimetableLock).filter(
        TimetableLock.timetable_id == timetable_id,
        TimetableLock.lock_type == body.lock_type,
        TimetableLock.entity_id == body.entity_id,
    ).first()
    if existing:
        return existing
    lock = TimetableLock(timetable_id=timetable_id, lock_type=body.lock_type, entity_id=body.entity_id)
    db.add(lock)
    db.commit()
    db.refresh(lock)
    return lock


@router.delete("/{timetable_id}/locks/{lock_id}", status_code=204)
def remove_lock(timetable_id: int, lock_id: int, db: Session = Depends(get_db)):
    lock = db.query(TimetableLock).filter(
        TimetableLock.id == lock_id,
        TimetableLock.timetable_id == timetable_id,
    ).first()
    if not lock:
        raise HTTPException(status_code=404, detail="Lock not found")
    db.delete(lock)
    db.commit()
