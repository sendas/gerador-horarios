from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import Cluster
from app.schemas.schemas import ClusterCreate, ClusterUpdate, ClusterResponse

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("", response_model=List[ClusterResponse])
def list_clusters(db: Session = Depends(get_db)):
    return db.query(Cluster).all()


@router.post("", response_model=ClusterResponse, status_code=201)
def create_cluster(data: ClusterCreate, db: Session = Depends(get_db)):
    existing = db.query(Cluster).filter(Cluster.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cluster with this name already exists")
    obj = Cluster(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{id}", response_model=ClusterResponse)
def get_cluster(id: int, db: Session = Depends(get_db)):
    obj = db.query(Cluster).filter(Cluster.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return obj


@router.put("/{id}", response_model=ClusterResponse)
def update_cluster(id: int, data: ClusterUpdate, db: Session = Depends(get_db)):
    obj = db.query(Cluster).filter(Cluster.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Cluster not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
def delete_cluster(id: int, db: Session = Depends(get_db)):
    obj = db.query(Cluster).filter(Cluster.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Cluster not found")
    db.delete(obj)
    db.commit()
