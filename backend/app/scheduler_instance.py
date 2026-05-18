"""APScheduler singleton for background jobs."""
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
_job_id = "auto_backup"


def start_scheduler():
    if not scheduler.running:
        scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)


def reschedule_backup(frequency: str | None):
    """Add/replace/remove the backup job based on frequency."""
    # Remove existing job if present
    if scheduler.get_job(_job_id):
        scheduler.remove_job(_job_id)
    if not frequency or frequency == "manual":
        return
    from app.routers.backup import run_backup_job
    trigger_kwargs = {
        "daily":   {"trigger": "interval", "hours": 24},
        "weekly":  {"trigger": "interval", "weeks": 1},
        "monthly": {"trigger": "interval", "days": 30},
    }.get(frequency, {"trigger": "interval", "weeks": 1})
    scheduler.add_job(run_backup_job, id=_job_id, **trigger_kwargs, replace_existing=True)
