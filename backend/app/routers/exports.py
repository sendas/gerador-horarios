from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.exports.html_export import generate_html_timetable
from app.exports.csv_export import generate_csv_timetable
from app.exports.excel_export import generate_excel_timetable

router = APIRouter(prefix="/timetables", tags=["exports"])


@router.get("/{id}/export/html", response_class=HTMLResponse)
def export_html(
    id: int,
    view: str = "class",
    entity_id: int = None,
    db: Session = Depends(get_db)
):
    html = generate_html_timetable(db, id, view, entity_id)
    return HTMLResponse(content=html)


@router.get("/{id}/export/csv")
def export_csv(
    id: int,
    view: str = "class",
    entity_id: int = None,
    db: Session = Depends(get_db)
):
    content = generate_csv_timetable(db, id, view, entity_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=horario_{id}.csv"}
    )


@router.get("/{id}/export/excel")
def export_excel(
    id: int,
    view: str = "class",
    entity_id: int = None,
    db: Session = Depends(get_db)
):
    content = generate_excel_timetable(db, id, view, entity_id)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=horario_{id}.xlsx"}
    )
