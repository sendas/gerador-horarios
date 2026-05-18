import json
import gzip
import os
import logging
from datetime import datetime
from typing import Optional

import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.models import BackupConfig, BackupHistory
from app.models import models as m
from app.auth import require_admin
from app.models.user import User

router = APIRouter(prefix="/backup", tags=["backup"])
logger = logging.getLogger(__name__)

MS_DEVICE_CODE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode"
MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MS_GRAPH_URL = "https://graph.microsoft.com/v1.0"
MS_SCOPE = "https://graph.microsoft.com/Files.ReadWrite offline_access"

APP_VERSION = "1.6.0"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _encrypt(value: str, secret: str) -> str:
    from cryptography.fernet import Fernet
    import base64, hashlib
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key).encrypt(value.encode()).decode()


def _decrypt(value: str, secret: str) -> str:
    from cryptography.fernet import Fernet
    import base64, hashlib
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key).decrypt(value.encode()).decode()


def _get_secret() -> str:
    return os.getenv("SECRET_KEY", "fallback-secret-key")


def model_to_dict(instance) -> dict:
    return {c.key: getattr(instance, c.key) for c in sa_inspect(instance).mapper.column_attrs}


def _build_backup_json(db: Session) -> bytes:
    """Serialise all tables to JSON (gzipped)."""
    tables = {
        "clusters":                   [model_to_dict(r) for r in db.query(m.Cluster).all()],
        "schools":                    [model_to_dict(r) for r in db.query(m.School).all()],
        "academic_years":             [model_to_dict(r) for r in db.query(m.AcademicYear).all()],
        "time_slot_configs":          [model_to_dict(r) for r in db.query(m.TimeSlotConfig).all()],
        "rooms":                      [model_to_dict(r) for r in db.query(m.Room).all()],
        "subjects":                   [model_to_dict(r) for r in db.query(m.Subject).all()],
        "classes":                    [model_to_dict(r) for r in db.query(m.Class).all()],
        "curriculum_entries":         [model_to_dict(r) for r in db.query(m.CurriculumEntry).all()],
        "teachers":                   [model_to_dict(r) for r in db.query(m.Teacher).all()],
        "teacher_school_assignments": [model_to_dict(r) for r in db.query(m.TeacherSchoolAssignment).all()],
        "teacher_subjects":           [model_to_dict(r) for r in db.query(m.TeacherSubject).all()],
        "teacher_availabilities":     [model_to_dict(r) for r in db.query(m.TeacherAvailability).all()],
        "non_teaching_types":         [model_to_dict(r) for r in db.query(m.NonTeachingType).all()],
        "non_teaching_assignments":   [model_to_dict(r) for r in db.query(m.NonTeachingAssignment).all()],
        "scheduling_rules":           [model_to_dict(r) for r in db.query(m.SchedulingRules).all()],
        "timetables":                 [model_to_dict(r) for r in db.query(m.Timetable).all()],
        "scheduled_lessons":          [model_to_dict(r) for r in db.query(m.ScheduledLesson).all()],
        "subject_groups":             [model_to_dict(r) for r in db.query(m.SubjectGroup).all()],
        "subject_group_entries":      [model_to_dict(r) for r in db.query(m.SubjectGroupEntry).all()],
    }
    payload = {
        "app_version": APP_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "tables": tables,
    }
    raw = json.dumps(payload, default=str, ensure_ascii=False, indent=2).encode("utf-8")
    return gzip.compress(raw)


def _get_access_token(refresh_token: str) -> str:
    """Use refresh_token to get a fresh access_token from Microsoft."""
    db = SessionLocal()
    try:
        cfg = db.query(BackupConfig).filter(BackupConfig.id == 1).first()
        client_id = cfg.onedrive_client_id if cfg else None
    finally:
        db.close()
    if not client_id:
        raise RuntimeError("client_id não configurado")
    resp = http_requests.post(MS_TOKEN_URL, data={
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": MS_SCOPE,
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _upload_to_onedrive(data: bytes, filename: str, folder: str, access_token: str):
    """Upload gzip data to OneDrive via Microsoft Graph."""
    url = f"{MS_GRAPH_URL}/me/drive/items/root:/{folder}/{filename}:/content"
    resp = http_requests.put(
        url, data=data,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/gzip"},
        timeout=120
    )
    resp.raise_for_status()


def run_backup_job():
    """Executed by APScheduler or triggered manually."""
    db = SessionLocal()
    try:
        cfg = db.query(BackupConfig).filter(BackupConfig.id == 1).first()
        if not cfg or not cfg.enabled:
            return
        data = _build_backup_json(db)
        filename = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json.gz"
        destination = "local"
        if cfg.onedrive_refresh_token:
            try:
                rt = _decrypt(cfg.onedrive_refresh_token, _get_secret())
                token = _get_access_token(rt)
                _upload_to_onedrive(data, filename, cfg.folder_path or "GeradorHorarios/Backups", token)
                destination = "onedrive"
            except Exception as e:
                logger.error(f"Erro ao enviar para OneDrive: {e}")
        # Record history
        db.add(BackupHistory(
            status="success", destination=destination,
            size_bytes=len(data), filename=filename
        ))
        cfg.last_backup_at = datetime.utcnow()
        db.commit()
        logger.info(f"Backup concluído: {filename} ({destination})")
    except Exception as e:
        db_inner = SessionLocal()
        try:
            db_inner.add(BackupHistory(status="error", message=str(e)))
            db_inner.commit()
        finally:
            db_inner.close()
        logger.error(f"Backup failed: {e}", exc_info=True)
    finally:
        db.close()


# ── Schemas ──────────────────────────────────────────────────────────────────

class BackupConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    frequency: Optional[str] = None
    onedrive_client_id: Optional[str] = None
    folder_path: Optional[str] = None


class DeviceCodeStart(BaseModel):
    client_id: str


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/config")
def get_config(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    cfg = db.query(BackupConfig).filter(BackupConfig.id == 1).first()
    if not cfg:
        cfg = BackupConfig(id=1)
        db.add(cfg); db.commit(); db.refresh(cfg)
    return {
        "enabled": cfg.enabled,
        "frequency": cfg.frequency,
        "onedrive_client_id": cfg.onedrive_client_id,
        "onedrive_connected": bool(cfg.onedrive_refresh_token),
        "folder_path": cfg.folder_path,
        "last_backup_at": cfg.last_backup_at,
        "next_backup_at": cfg.next_backup_at,
    }


@router.put("/config")
def update_config(
    data: BackupConfigUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    cfg = db.query(BackupConfig).filter(BackupConfig.id == 1).first()
    if not cfg:
        cfg = BackupConfig(id=1)
        db.add(cfg)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(cfg, field, value)
    db.commit()
    db.refresh(cfg)
    # Reschedule if frequency changed
    from app.scheduler_instance import reschedule_backup
    reschedule_backup(cfg.frequency if cfg.enabled else None)
    return {"ok": True}


@router.post("/onedrive/start-auth")
def start_onedrive_auth(body: DeviceCodeStart, _: User = Depends(require_admin)):
    resp = http_requests.post(MS_DEVICE_CODE_URL, data={
        "client_id": body.client_id,
        "scope": MS_SCOPE,
    }, timeout=30)
    if not resp.ok:
        raise HTTPException(400, f"Erro Microsoft: {resp.text}")
    d = resp.json()
    return {
        "device_code": d["device_code"],
        "user_code": d["user_code"],
        "verification_uri": d["verification_uri"],
        "expires_in": d["expires_in"],
        "interval": d.get("interval", 5),
        "message": d.get("message", ""),
    }


class PollAuthRequest(BaseModel):
    client_id: str
    device_code: str


@router.post("/onedrive/poll-auth")
def poll_onedrive_auth(
    body: PollAuthRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    resp = http_requests.post(MS_TOKEN_URL, data={
        "client_id": body.client_id,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": body.device_code,
    }, timeout=30)
    d = resp.json()
    if "error" in d:
        if d["error"] == "authorization_pending":
            return {"status": "pending"}
        raise HTTPException(400, d.get("error_description", d["error"]))
    # Success — save refresh token encrypted
    cfg = db.query(BackupConfig).filter(BackupConfig.id == 1).first()
    if not cfg:
        cfg = BackupConfig(id=1)
        db.add(cfg)
    cfg.onedrive_client_id = body.client_id
    cfg.onedrive_refresh_token = _encrypt(d["refresh_token"], _get_secret())
    db.commit()
    return {"status": "ok", "account": d.get("id_token", "")[:50]}


@router.delete("/onedrive/disconnect")
def disconnect_onedrive(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    cfg = db.query(BackupConfig).filter(BackupConfig.id == 1).first()
    if cfg:
        cfg.onedrive_refresh_token = None
        db.commit()
    return {"ok": True}


@router.post("/now")
def backup_now(
    background_tasks: BackgroundTasks,
    _: User = Depends(require_admin),
):
    background_tasks.add_task(run_backup_job)
    return {"message": "Backup iniciado em segundo plano"}


@router.get("/download")
def download_backup(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    data = _build_backup_json(db)
    filename = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json.gz"
    db.add(BackupHistory(status="success", destination="download", size_bytes=len(data), filename=filename))
    db.commit()
    return Response(
        content=data,
        media_type="application/gzip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/history")
def get_history(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.query(BackupHistory).order_by(BackupHistory.created_at.desc()).limit(20).all()
    return [model_to_dict(r) for r in rows]
