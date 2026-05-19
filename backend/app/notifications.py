import logging
import requests

logger = logging.getLogger(__name__)

PUSHBULLET_URL = "https://api.pushbullet.com/v2/pushes"


def send_pushbullet(token: str, title: str, body: str) -> bool:
    """Send a Pushbullet note. Returns True on success."""
    try:
        resp = requests.post(
            PUSHBULLET_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"type": "note", "title": title, "body": body},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Pushbullet notification failed: %s", exc)
        return False


def get_setting(db, key: str) -> str | None:
    from app.models.models import AppSetting
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return row.value if row else None


def notify_timetable_done(db, timetable_name: str, status: str, detail: str = "") -> None:
    token = get_setting(db, "pushbullet_token")
    if not token:
        return
    if status == "done":
        title = "Sinaptik — Horário concluído ✓"
        body = f"O horário «{timetable_name}» foi gerado com sucesso."
    else:
        title = "Sinaptik — Erro na geração ✗"
        body = f"O horário «{timetable_name}» falhou.\n{detail[:200]}" if detail else f"O horário «{timetable_name}» falhou."
    send_pushbullet(token, title, body)
