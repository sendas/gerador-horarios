from datetime import date as date_type
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.models import (
    Teacher, TeacherSchoolAssignment, TeacherSubject, TeacherAvailability,
    CurriculumEntry, Class, Subject
)
from app.schemas.schemas import (
    TeacherCreate, TeacherUpdate, TeacherResponse,
    TeacherSchoolAssignmentCreate, TeacherSchoolAssignmentResponse,
    TeacherAvailabilityCreate, TeacherAvailabilityResponse, TeacherAvailabilityBulk
)

router = APIRouter(prefix="/teachers", tags=["teachers"])


class BulkTeacherUpdate(BaseModel):
    id: int
    teaching_component: Optional[int] = None
    credit_hours: Optional[int] = None
    birth_date: Optional[date_type] = None
    total_hours: Optional[int] = None
    base_teaching_hours: Optional[int] = None
    te_hours: Optional[int] = None
    te_role: Optional[str] = None
    credit_role: Optional[str] = None


class BulkComponentRequest(BaseModel):
    cluster_id: int
    base_component: int = 22
    apply_art79: bool = False


class BulkFreeDayRequest(BaseModel):
    cluster_id: int
    day: Optional[int] = None  # 0=Seg … 4=Sex, None = limpar


class BlockedSlot(BaseModel):
    day_of_week: int
    slot_number: int


class BulkAvailabilityRequest(BaseModel):
    cluster_id: int
    academic_year_id: int
    blocked_slots: List[BlockedSlot]


def _build_response(t: Teacher) -> TeacherResponse:
    r = TeacherResponse.model_validate(t)
    r.subject_names = sorted(ts.subject.name for ts in t.teacher_subjects if ts.subject)
    r.subject_ids = [ts.subject_id for ts in t.teacher_subjects]
    r.school_ids = list({sa.school_id for sa in t.school_assignments})
    primary = next((sa for sa in t.school_assignments if sa.is_primary), None)
    r.primary_school_id = primary.school_id if primary else None
    r.primary_school_name = primary.school.name if primary and primary.school else None
    return r


def _sa_dict(sa: TeacherSchoolAssignment) -> dict:
    return {
        "id": sa.id,
        "teacher_id": sa.teacher_id,
        "school_id": sa.school_id,
        "academic_year_id": sa.academic_year_id,
        "travel_time_minutes": sa.travel_time_minutes,
        "is_primary": bool(sa.is_primary),
        "school_name": sa.school.name if sa.school else None,
    }


@router.post("/bulk-free-day")
def bulk_set_free_day(req: BulkFreeDayRequest, db: Session = Depends(get_db)):
    """Set the same preferred free day (or clear it) for ALL teachers in a cluster."""
    updated = db.query(Teacher).filter(Teacher.cluster_id == req.cluster_id).update(
        {"preferred_free_day": req.day}, synchronize_session=False
    )
    db.commit()
    day_names = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
    day_label = day_names[req.day] if req.day is not None else "nenhum (limpo)"
    return {"updated": updated, "day": req.day, "message": f"Dia livre definido como {day_label} para {updated} professor(es)."}


@router.post("/bulk-availability")
def bulk_set_availability(req: BulkAvailabilityRequest, db: Session = Depends(get_db)):
    """Replace all TeacherAvailability records for a cluster+year with the given blocked slots."""
    teacher_ids = [t.id for t in db.query(Teacher).filter(Teacher.cluster_id == req.cluster_id).all()]
    if not teacher_ids:
        return {"updated": 0, "blocked_slots": 0, "message": "Nenhum professor encontrado."}
    db.query(TeacherAvailability).filter(
        TeacherAvailability.teacher_id.in_(teacher_ids),
        TeacherAvailability.academic_year_id == req.academic_year_id,
    ).delete(synchronize_session=False)
    objs = [
        TeacherAvailability(
            teacher_id=tid,
            academic_year_id=req.academic_year_id,
            day_of_week=s.day_of_week,
            slot_number=s.slot_number,
            is_available=False,
        )
        for tid in teacher_ids
        for s in req.blocked_slots
    ]
    if objs:
        db.add_all(objs)
    db.commit()
    return {
        "updated": len(teacher_ids),
        "blocked_slots": len(req.blocked_slots),
        "message": f"Disponibilidade definida para {len(teacher_ids)} professor(es), {len(req.blocked_slots)} bloco(s) bloqueado(s).",
    }


@router.put("/bulk-update")
def bulk_update_teachers(items: List[BulkTeacherUpdate], db: Session = Depends(get_db)):
    updated = []
    for item in items:
        t = db.query(Teacher).filter(Teacher.id == item.id).first()
        if not t:
            continue
        if item.teaching_component is not None:
            t.teaching_component = item.teaching_component
        # Always persist these fields (allow clearing with null/0)
        t.credit_hours = item.credit_hours if item.credit_hours is not None else 0
        t.birth_date = item.birth_date
        t.credit_role = item.credit_role
        t.te_role = item.te_role
        if item.total_hours is not None:
            t.total_hours = item.total_hours
        if item.base_teaching_hours is not None:
            t.base_teaching_hours = item.base_teaching_hours
        if item.te_hours is not None:
            t.te_hours = item.te_hours
        updated.append(t.id)
    db.commit()
    return {"updated": updated}


@router.put("/bulk-component")
def bulk_set_component(data: BulkComponentRequest, db: Session = Depends(get_db)):
    """Set teaching_component for all teachers in a cluster.
    If apply_art79=True, applies Art. 79° ECD age-based reductions on top of base_component."""
    teachers_list = db.query(Teacher).filter(Teacher.cluster_id == data.cluster_id).all()
    today = date_type.today()
    updated = 0
    for t in teachers_list:
        component = data.base_component
        if data.apply_art79 and t.birth_date:
            age = (today - t.birth_date).days // 365
            if age >= 60:
                component -= 3
            elif age >= 55:
                component -= 2
            elif age >= 50:
                component -= 1
        t.teaching_component = component
        updated += 1
    db.commit()
    return {"updated": updated}


@router.get("", response_model=List[TeacherResponse])
def list_teachers(cluster_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Teacher)
    if cluster_id:
        q = q.filter(Teacher.cluster_id == cluster_id)
    return [_build_response(t) for t in q.all()]


@router.post("", response_model=TeacherResponse, status_code=201)
def create_teacher(data: TeacherCreate, db: Session = Depends(get_db)):
    obj = Teacher(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _build_response(obj)


@router.get("/{id}", response_model=TeacherResponse)
def get_teacher(id: int, db: Session = Depends(get_db)):
    obj = db.query(Teacher).filter(Teacher.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return _build_response(obj)


@router.put("/{id}", response_model=TeacherResponse)
def update_teacher(id: int, data: TeacherUpdate, db: Session = Depends(get_db)):
    obj = db.query(Teacher).filter(Teacher.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Teacher not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return _build_response(obj)


@router.delete("/{id}", status_code=204)
def delete_teacher(id: int, db: Session = Depends(get_db)):
    obj = db.query(Teacher).filter(Teacher.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Teacher not found")
    db.delete(obj)
    db.commit()


@router.get("/{id}/curriculum")
def list_teacher_curriculum(id: int, academic_year_id: int = None, db: Session = Depends(get_db)):
    """Return all curriculum entries assigned to this teacher, with class/subject names."""
    q = db.query(CurriculumEntry).filter(CurriculumEntry.teacher_id == id)
    if academic_year_id:
        q = q.join(Class).filter(Class.academic_year_id == academic_year_id)
    entries = q.all()
    return [{
        "id": e.id,
        "class_id": e.class_id,
        "class_name": e.class_.name if e.class_ else "",
        "year_level": e.class_.year_level if e.class_ else 0,
        "subject_id": e.subject_id,
        "subject_name": e.subject.name if e.subject else "",
        "hours_per_week": e.hours_per_week,
        "teacher_id": e.teacher_id,
    } for e in entries]


# School assignments

@router.get("/{id}/school-assignments")
def list_school_assignments(id: int, db: Session = Depends(get_db)):
    rows = db.query(TeacherSchoolAssignment).filter(TeacherSchoolAssignment.teacher_id == id).all()
    return [_sa_dict(sa) for sa in rows]


@router.post("/{id}/school-assignments", status_code=201)
def add_school_assignment(id: int, data: TeacherSchoolAssignmentCreate, db: Session = Depends(get_db)):
    # If marked primary, unset previous primary for this teacher+year
    if data.is_primary:
        db.query(TeacherSchoolAssignment).filter(
            TeacherSchoolAssignment.teacher_id == id,
            TeacherSchoolAssignment.academic_year_id == data.academic_year_id,
            TeacherSchoolAssignment.is_primary == True,
        ).update({"is_primary": False})
    obj = TeacherSchoolAssignment(**{**data.model_dump(exclude={"teacher_id"}), "teacher_id": id})
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _sa_dict(obj)


@router.patch("/school-assignments/{assignment_id}/set-primary", status_code=200)
def set_primary_school(assignment_id: int, db: Session = Depends(get_db)):
    """Mark this assignment as the teacher's primary school for its academic year."""
    obj = db.query(TeacherSchoolAssignment).filter(TeacherSchoolAssignment.id == assignment_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Assignment not found")
    # Unset any existing primary for same teacher+year
    db.query(TeacherSchoolAssignment).filter(
        TeacherSchoolAssignment.teacher_id == obj.teacher_id,
        TeacherSchoolAssignment.academic_year_id == obj.academic_year_id,
        TeacherSchoolAssignment.is_primary == True,
    ).update({"is_primary": False})
    obj.is_primary = True
    db.commit()
    db.refresh(obj)
    return _sa_dict(obj)


@router.delete("/school-assignments/{assignment_id}", status_code=204)
def delete_school_assignment(assignment_id: int, db: Session = Depends(get_db)):
    obj = db.query(TeacherSchoolAssignment).filter(TeacherSchoolAssignment.id == assignment_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(obj)
    db.commit()


# Subject assignments

@router.get("/{id}/subjects")
def list_teacher_subjects(id: int, db: Session = Depends(get_db)):
    rows = db.query(TeacherSubject).filter(TeacherSubject.teacher_id == id).all()
    return [{"id": r.id, "teacher_id": r.teacher_id, "subject_id": r.subject_id} for r in rows]


@router.post("/{id}/subjects/{subject_id}", status_code=201)
def add_teacher_subject(id: int, subject_id: int, db: Session = Depends(get_db)):
    existing = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == id,
        TeacherSubject.subject_id == subject_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Assignment already exists")
    obj = TeacherSubject(teacher_id=id, subject_id=subject_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"id": obj.id, "teacher_id": obj.teacher_id, "subject_id": obj.subject_id}


@router.delete("/{id}/subjects/{subject_id}", status_code=204)
def remove_teacher_subject(id: int, subject_id: int, db: Session = Depends(get_db)):
    obj = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == id,
        TeacherSubject.subject_id == subject_id
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(obj)
    db.commit()


# Availability

@router.get("/{id}/availability", response_model=List[TeacherAvailabilityResponse])
def get_availability(id: int, academic_year_id: int = None, db: Session = Depends(get_db)):
    q = db.query(TeacherAvailability).filter(TeacherAvailability.teacher_id == id)
    if academic_year_id:
        q = q.filter(TeacherAvailability.academic_year_id == academic_year_id)
    return q.all()


@router.post("/{id}/availability/bulk", response_model=List[TeacherAvailabilityResponse])
def set_availability_bulk(id: int, data: TeacherAvailabilityBulk, db: Session = Depends(get_db)):
    db.query(TeacherAvailability).filter(
        TeacherAvailability.teacher_id == id,
        TeacherAvailability.academic_year_id == data.academic_year_id
    ).delete(synchronize_session=False)
    objs = [
        TeacherAvailability(
            teacher_id=id,
            academic_year_id=data.academic_year_id,
            day_of_week=a.day_of_week,
            slot_number=a.slot_number,
            is_available=a.is_available,
        )
        for a in data.availabilities
    ]
    db.add_all(objs)
    db.commit()
    for obj in objs:
        db.refresh(obj)
    return objs
