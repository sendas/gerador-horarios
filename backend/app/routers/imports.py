import csv
import io
import os
import base64
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Teacher, Class, Room, Cluster, School
from app.auth import require_editor
from app.models.user import User

router = APIRouter(prefix="/imports", tags=["imports"])


def parse_upload(file: UploadFile) -> List[Dict[str, Any]]:
    """Parse CSV or XLSX file into list of dicts using headers from first row."""
    filename = file.filename or ""
    content = file.file.read()

    if filename.lower().endswith(".csv"):
        text = content.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]

    elif filename.lower().endswith((".xlsx", ".xls")):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(h).strip() if h is not None else "" for h in rows[0]]
        result = []
        for row in rows[1:]:
            if all(v is None for v in row):
                continue
            result.append({headers[i]: (str(row[i]).strip() if row[i] is not None else "") for i in range(len(headers))})
        return result
    else:
        raise HTTPException(status_code=400, detail="Formato de ficheiro não suportado. Use .csv ou .xlsx")


def get_col(row: Dict[str, Any], *names: str, default: Any = None) -> Any:
    """Get first matching column value from a row dict (case-insensitive)."""
    for name in names:
        for key in row:
            if key.strip().lower() == name.lower():
                val = row[key]
                if val is not None and str(val).strip() != "":
                    return str(val).strip()
    return default


@router.post("/teachers")
def import_teachers(
    file: UploadFile = File(...),
    cluster_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Import teachers from CSV/XLSX file."""
    # Verify cluster exists
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Agrupamento não encontrado")

    rows = parse_upload(file)

    created = 0
    skipped = 0
    errors: List[str] = []

    for i, row in enumerate(rows, start=2):
        name = get_col(row, "nome", "name", "Nome")
        if not name:
            errors.append(f"Linha {i}: nome em falta")
            continue

        # Check duplicate
        existing = db.query(Teacher).filter(
            Teacher.cluster_id == cluster_id,
            Teacher.name == name,
        ).first()
        if existing:
            skipped += 1
            continue

        email = get_col(row, "email", "Email") or None
        max_aulas_raw = get_col(row, "max_aulas_dia", "max_daily_lessons")
        try:
            max_daily = int(max_aulas_raw) if max_aulas_raw else 5
        except ValueError:
            max_daily = 5

        teacher = Teacher(
            cluster_id=cluster_id,
            name=name,
            email=email,
            max_daily_lessons=max_daily,
        )
        db.add(teacher)
        created += 1

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


@router.post("/classes")
def import_classes(
    file: UploadFile = File(...),
    school_id: int = Form(...),
    academic_year_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Import classes from CSV/XLSX file."""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="Escola não encontrada")

    rows = parse_upload(file)

    created = 0
    skipped = 0
    errors: List[str] = []

    for i, row in enumerate(rows, start=2):
        name = get_col(row, "nome", "turma", "Nome", "name")
        if not name:
            errors.append(f"Linha {i}: nome em falta")
            continue

        # Check duplicate
        existing = db.query(Class).filter(
            Class.school_id == school_id,
            Class.academic_year_id == academic_year_id,
            Class.name == name,
        ).first()
        if existing:
            skipped += 1
            continue

        year_raw = get_col(row, "ano", "year_level", "Ano")
        try:
            year_level = int(year_raw) if year_raw else 5
        except ValueError:
            year_level = 5

        alunos_raw = get_col(row, "alunos", "num_students", "Alunos")
        try:
            num_students = int(alunos_raw) if alunos_raw else 25
        except ValueError:
            num_students = 25

        cls = Class(
            school_id=school_id,
            academic_year_id=academic_year_id,
            name=name,
            year_level=year_level,
            num_students=num_students,
        )
        db.add(cls)
        created += 1

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


@router.post("/rooms")
def import_rooms(
    file: UploadFile = File(...),
    school_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Import rooms from CSV/XLSX file."""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="Escola não encontrada")

    rows = parse_upload(file)

    created = 0
    skipped = 0
    errors: List[str] = []

    for i, row in enumerate(rows, start=2):
        name = get_col(row, "nome", "sala", "Nome", "name")
        if not name:
            errors.append(f"Linha {i}: nome em falta")
            continue

        # Check duplicate
        existing = db.query(Room).filter(
            Room.school_id == school_id,
            Room.name == name,
        ).first()
        if existing:
            skipped += 1
            continue

        cap_raw = get_col(row, "capacidade", "capacity", "Capacidade")
        try:
            capacity = int(cap_raw) if cap_raw else 30
        except ValueError:
            capacity = 30

        room_type = get_col(row, "tipo", "room_type", "Tipo") or "classroom"

        room = Room(
            school_id=school_id,
            name=name,
            capacity=capacity,
            room_type=room_type,
        )
        db.add(room)
        created += 1

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


@router.post("/image")
def import_from_image(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Extract structured data from an image using Claude Vision API."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY não configurada. Funcionalidade de importação por imagem indisponível.",
        )

    import anthropic

    # Read image and encode as base64
    image_content = file.file.read()
    image_b64 = base64.standard_b64encode(image_content).decode("utf-8")

    # Detect media type
    filename = file.filename or ""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    media_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    media_type = media_type_map.get(ext, "image/jpeg")

    # Build prompt based on entity_type
    prompts = {
        "teachers": (
            "Analisa esta imagem e extrai uma lista de professores. "
            "Devolve um array JSON com objetos contendo os campos: "
            "'nome' (nome completo do professor), 'email' (endereço de email, se visível), "
            "'max_aulas_dia' (número máximo de aulas por dia, se indicado, senão omite). "
            "Devolve apenas o array JSON sem explicações adicionais."
        ),
        "classes": (
            "Analisa esta imagem e extrai uma lista de turmas escolares. "
            "Devolve um array JSON com objetos contendo os campos: "
            "'nome' (nome/designação da turma), 'ano' (ano de escolaridade, número), "
            "'alunos' (número de alunos, se indicado, senão omite). "
            "Devolve apenas o array JSON sem explicações adicionais."
        ),
        "rooms": (
            "Analisa esta imagem e extrai uma lista de salas de aula. "
            "Devolve um array JSON com objetos contendo os campos: "
            "'nome' (nome/número da sala), 'capacidade' (capacidade em número de alunos, se indicado), "
            "'tipo' (tipo de sala, ex: 'classroom', 'lab', 'gym', se indicado). "
            "Devolve apenas o array JSON sem explicações adicionais."
        ),
        "time_slots": (
            "Analisa esta imagem e extrai uma lista de tempos letivos/horários. "
            "Devolve um array JSON com objetos contendo os campos: "
            "'slot_number' (número do tempo), 'start_time' (hora de início em formato HH:MM), "
            "'end_time' (hora de fim em formato HH:MM), 'day_of_week' (dia da semana: 0=segunda a 4=sexta, se indicado). "
            "Devolve apenas o array JSON sem explicações adicionais."
        ),
    }

    prompt = prompts.get(
        entity_type,
        "Analisa esta imagem e extrai os dados em formato JSON. Devolve apenas o array JSON.",
    )

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    import json

    raw_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1]) if len(lines) > 2 else raw_text

    try:
        extracted_data = json.loads(raw_text)
        if not isinstance(extracted_data, list):
            extracted_data = [extracted_data]
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=422,
            detail=f"Não foi possível interpretar a resposta da IA como JSON: {raw_text[:200]}",
        )

    return {"data": extracted_data, "entity_type": entity_type}
