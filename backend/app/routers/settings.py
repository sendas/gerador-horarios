from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.models import AppSetting
from app.notifications import send_pushbullet

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingUpsert(BaseModel):
    value: Optional[str] = None


class PushbulletTest(BaseModel):
    token: str


@router.get("")
def get_all_settings(db: Session = Depends(get_db)):
    rows = db.query(AppSetting).all()
    return {r.key: r.value for r in rows}


@router.put("/{key}")
def upsert_setting(key: str, data: SettingUpsert, db: Session = Depends(get_db)):
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = data.value
    else:
        row = AppSetting(key=key, value=data.value)
        db.add(row)
    db.commit()
    return {"key": key, "value": data.value}


@router.post("/test-pushbullet")
def test_pushbullet(data: PushbulletTest):
    ok = send_pushbullet(
        data.token,
        "Sinaptik — Teste de notificação",
        "A configuração do Pushbullet está a funcionar corretamente.",
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Falha ao enviar notificação. Verifique o token.")
    return {"ok": True}
