from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.models import (
    CurriculumPlan, CurriculumEntry, Class, Subject, School, AcademicYear, Cluster
)

router = APIRouter(prefix="/curriculum-plans", tags=["curriculum-plans"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class PlanEntry(BaseModel):
    id: Optional[int] = None
    cluster_id: int
    academic_year_id: int
    year_level: int
    subject_id: int
    hours_per_week: float
    weekly_structure: str = "1+1"
    subject_name: Optional[str] = None
    subject_color: Optional[str] = None

    class Config:
        from_attributes = True


class PlanCreate(BaseModel):
    cluster_id: int
    academic_year_id: int
    year_level: int
    subject_id: int
    hours_per_week: float
    weekly_structure: str = "1+1"


class PlanUpdate(BaseModel):
    hours_per_week: Optional[float] = None
    weekly_structure: Optional[str] = None


class ApplyRequest(BaseModel):
    cluster_id: int
    academic_year_id: int
    year_levels: Optional[List[int]] = None  # None = all year levels in plan
    overwrite: bool = False  # if True, delete existing entries before applying


class CopyRequest(BaseModel):
    cluster_id: int
    from_academic_year_id: int
    to_academic_year_id: int
    year_levels: Optional[List[int]] = None  # None = copy all
    overwrite: bool = True  # if True, replace existing plans in target year


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_structure(ws: str):
    """'2+1' -> (split_count=3, consecutive_pairs=1, is_split=True)"""
    if not ws or ws.strip() == "1":
        return 1, 0, False
    try:
        parts = [int(p) for p in ws.strip().split("+")]
    except ValueError:
        return 1, 0, False
    split_count = sum(parts)
    consecutive_pairs = sum(1 for p in parts if p >= 2)
    return split_count, consecutive_pairs, split_count > 1


def _plan_to_dict(p: CurriculumPlan) -> dict:
    return {
        "id": p.id,
        "cluster_id": p.cluster_id,
        "academic_year_id": p.academic_year_id,
        "year_level": p.year_level,
        "subject_id": p.subject_id,
        "hours_per_week": p.hours_per_week,
        "weekly_structure": p.weekly_structure,
        "subject_name": p.subject.name if p.subject else None,
        "subject_color": p.subject.color if p.subject else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
def list_plans(
    cluster_id: int,
    academic_year_id: int,
    year_level: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(CurriculumPlan).filter(
        CurriculumPlan.cluster_id == cluster_id,
        CurriculumPlan.academic_year_id == academic_year_id,
    )
    if year_level is not None:
        q = q.filter(CurriculumPlan.year_level == year_level)
    plans = q.order_by(CurriculumPlan.year_level, CurriculumPlan.id).all()
    return [_plan_to_dict(p) for p in plans]


@router.post("", status_code=201)
def create_plan(data: PlanCreate, db: Session = Depends(get_db)):
    existing = db.query(CurriculumPlan).filter(
        CurriculumPlan.cluster_id == data.cluster_id,
        CurriculumPlan.academic_year_id == data.academic_year_id,
        CurriculumPlan.year_level == data.year_level,
        CurriculumPlan.subject_id == data.subject_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Entrada já existe para este ano/disciplina")
    p = CurriculumPlan(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _plan_to_dict(p)


@router.put("/{id}")
def update_plan(id: int, data: PlanUpdate, db: Session = Depends(get_db)):
    p = db.query(CurriculumPlan).filter(CurriculumPlan.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Entrada não encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return _plan_to_dict(p)


@router.delete("/{id}", status_code=204)
def delete_plan(id: int, db: Session = Depends(get_db)):
    p = db.query(CurriculumPlan).filter(CurriculumPlan.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Entrada não encontrada")
    db.delete(p)
    db.commit()


@router.post("/apply")
def apply_plan(req: ApplyRequest, db: Session = Depends(get_db)):
    """Apply curriculum plans to all matching classes, creating CurriculumEntry records."""
    q = db.query(CurriculumPlan).filter(
        CurriculumPlan.cluster_id == req.cluster_id,
        CurriculumPlan.academic_year_id == req.academic_year_id,
    )
    if req.year_levels:
        q = q.filter(CurriculumPlan.year_level.in_(req.year_levels))
    plans = q.all()

    if not plans:
        return {"created": 0, "skipped": 0, "classes": 0, "message": "Nenhum plano encontrado."}

    # Find all classes in scope
    school_ids = [s.id for s in db.query(School).filter(School.cluster_id == req.cluster_id).all()]
    year_levels_in_plans = list({p.year_level for p in plans})
    classes = db.query(Class).filter(
        Class.school_id.in_(school_ids),
        Class.academic_year_id == req.academic_year_id,
        Class.year_level.in_(year_levels_in_plans),
    ).all()

    if not classes:
        return {"created": 0, "skipped": 0, "classes": 0, "message": "Nenhuma turma encontrada para os anos de escolaridade do plano."}

    # Group plans by year_level
    plans_by_yl: dict = {}
    for p in plans:
        plans_by_yl.setdefault(p.year_level, []).append(p)

    created = skipped = 0
    for cls in classes:
        yl_plans = plans_by_yl.get(cls.year_level, [])
        for plan in yl_plans:
            exists = db.query(CurriculumEntry).filter(
                CurriculumEntry.class_id == cls.id,
                CurriculumEntry.subject_id == plan.subject_id,
            ).first()
            if exists:
                if req.overwrite:
                    exists.hours_per_week = plan.hours_per_week
                    exists.weekly_structure = plan.weekly_structure
                    sc, cp, is_split = _parse_structure(plan.weekly_structure)
                    exists.is_split = is_split
                    exists.split_count = sc
                    exists.consecutive_pairs = cp
                    created += 1
                else:
                    skipped += 1
                continue
            sc, cp, is_split = _parse_structure(plan.weekly_structure)
            entry = CurriculumEntry(
                class_id=cls.id,
                subject_id=plan.subject_id,
                hours_per_week=plan.hours_per_week,
                weekly_structure=plan.weekly_structure,
                is_split=is_split,
                split_count=sc,
                consecutive_pairs=cp,
            )
            db.add(entry)
            created += 1

    db.commit()
    return {
        "created": created,
        "skipped": skipped,
        "classes": len(classes),
        "message": f"{created} entrada(s) criada(s)/atualizada(s) em {len(classes)} turma(s). {skipped} já existiam (ignoradas).",
    }


@router.post("/copy")
def copy_plan(req: CopyRequest, db: Session = Depends(get_db)):
    """Copy curriculum plans from one academic year to another."""
    if req.from_academic_year_id == req.to_academic_year_id:
        raise HTTPException(status_code=400, detail="Anos letivos de origem e destino são iguais.")

    q = db.query(CurriculumPlan).filter(
        CurriculumPlan.cluster_id == req.cluster_id,
        CurriculumPlan.academic_year_id == req.from_academic_year_id,
    )
    if req.year_levels:
        q = q.filter(CurriculumPlan.year_level.in_(req.year_levels))
    source_plans = q.all()

    if not source_plans:
        return {"copied": 0, "message": "Nenhum plano encontrado no ano de origem."}

    if req.overwrite:
        del_q = db.query(CurriculumPlan).filter(
            CurriculumPlan.cluster_id == req.cluster_id,
            CurriculumPlan.academic_year_id == req.to_academic_year_id,
        )
        if req.year_levels:
            del_q = del_q.filter(CurriculumPlan.year_level.in_(req.year_levels))
        del_q.delete(synchronize_session=False)

    copied = skipped = 0
    for src in source_plans:
        if not req.overwrite:
            exists = db.query(CurriculumPlan).filter(
                CurriculumPlan.cluster_id == req.cluster_id,
                CurriculumPlan.academic_year_id == req.to_academic_year_id,
                CurriculumPlan.year_level == src.year_level,
                CurriculumPlan.subject_id == src.subject_id,
            ).first()
            if exists:
                skipped += 1
                continue
        new_p = CurriculumPlan(
            cluster_id=req.cluster_id,
            academic_year_id=req.to_academic_year_id,
            year_level=src.year_level,
            subject_id=src.subject_id,
            hours_per_week=src.hours_per_week,
            weekly_structure=src.weekly_structure,
        )
        db.add(new_p)
        copied += 1

    db.commit()
    from_year = db.query(AcademicYear).filter(AcademicYear.id == req.from_academic_year_id).first()
    to_year = db.query(AcademicYear).filter(AcademicYear.id == req.to_academic_year_id).first()
    return {
        "copied": copied,
        "skipped": skipped,
        "message": (
            f"{copied} entrada(s) copiada(s) de '{from_year.name if from_year else req.from_academic_year_id}' "
            f"para '{to_year.name if to_year else req.to_academic_year_id}'. "
            + (f"{skipped} já existiam (ignoradas)." if skipped else "")
        ),
    }


@router.get("/year-levels")
def list_year_levels(cluster_id: int, academic_year_id: int, db: Session = Depends(get_db)):
    """Return distinct year levels that have plans defined."""
    rows = db.query(CurriculumPlan.year_level).filter(
        CurriculumPlan.cluster_id == cluster_id,
        CurriculumPlan.academic_year_id == academic_year_id,
    ).distinct().order_by(CurriculumPlan.year_level).all()
    return [r[0] for r in rows]
