from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.models import SchedulingRules
from app.auth import require_editor, require_admin
from app.models.user import User

router = APIRouter(prefix="/scheduling-rules", tags=["scheduling-rules"])


class SchedulingRulesCreate(BaseModel):
    cluster_id: int
    academic_year_id: Optional[int] = None
    max_periods_per_day_class: int = 5
    max_periods_per_day_teacher: int = 6
    max_consecutive_periods_class: int = 2
    max_consecutive_periods_teacher: int = 4
    avoid_isolated_teacher: bool = False
    no_student_gaps: bool = True
    minimize_teacher_gaps: bool = True
    teacher_gap_weight: int = 10
    no_same_subject_twice_per_day: bool = True
    distribute_subjects_weight: int = 5
    students_start_slot_1: bool = True
    no_pe_after_lunch: bool = True
    lunch_after_slot: int = 4


class SchedulingRulesUpdate(BaseModel):
    max_periods_per_day_class: Optional[int] = None
    max_periods_per_day_teacher: Optional[int] = None
    max_consecutive_periods_class: Optional[int] = None
    max_consecutive_periods_teacher: Optional[int] = None
    avoid_isolated_teacher: Optional[bool] = None
    no_student_gaps: Optional[bool] = None
    minimize_teacher_gaps: Optional[bool] = None
    teacher_gap_weight: Optional[int] = None
    no_same_subject_twice_per_day: Optional[bool] = None
    distribute_subjects_weight: Optional[int] = None
    students_start_slot_1: Optional[bool] = None
    no_pe_after_lunch: Optional[bool] = None
    lunch_after_slot: Optional[int] = None


class SchedulingRulesResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    cluster_id: int
    academic_year_id: Optional[int]
    max_periods_per_day_class: int
    max_periods_per_day_teacher: int
    max_consecutive_periods_class: int
    max_consecutive_periods_teacher: int
    avoid_isolated_teacher: bool
    no_student_gaps: bool = True
    minimize_teacher_gaps: bool = True
    teacher_gap_weight: int = 10
    no_same_subject_twice_per_day: bool = True
    distribute_subjects_weight: int = 5
    students_start_slot_1: bool = True
    no_pe_after_lunch: bool = True
    lunch_after_slot: int = 4


@router.get("", response_model=List[SchedulingRulesResponse])
def list_rules(cluster_id: int = None, db: Session = Depends(get_db)):
    q = db.query(SchedulingRules)
    if cluster_id:
        q = q.filter(SchedulingRules.cluster_id == cluster_id)
    return q.all()


@router.post("", response_model=SchedulingRulesResponse, status_code=201)
def create_rules(data: SchedulingRulesCreate, db: Session = Depends(get_db), _: User = Depends(require_editor)):
    obj = SchedulingRules(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{id}", response_model=SchedulingRulesResponse)
def update_rules(id: int, data: SchedulingRulesUpdate, db: Session = Depends(get_db), _: User = Depends(require_editor)):
    obj = db.query(SchedulingRules).filter(SchedulingRules.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
def delete_rules(id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    obj = db.query(SchedulingRules).filter(SchedulingRules.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Não encontrado")
    db.delete(obj)
    db.commit()
