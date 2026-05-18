import csv
import io
import os
import base64
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Teacher, Class, Room, Cluster, School, Subject, CurriculumEntry, TeacherSubject, TeacherSchoolAssignment
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


@router.post("/curriculum")
def import_curriculum(
    file: UploadFile = File(...),
    cluster_id: int = Form(...),
    school_id: int = Form(...),
    academic_year_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Import full curriculum from CSV/XLSX: creates classes, subjects, teachers and curriculum entries.

    Expected columns: ano, turma, disciplina, horas semana, professor, articulado
    The column 'ano+turma+disc' is accepted but ignored (used as key in source data).
    """
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="Escola não encontrada")
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Agrupamento não encontrado")

    rows = parse_upload(file)

    stats = {"classes": 0, "subjects": 0, "teachers": 0, "entries": 0, "skipped": 0}
    errors: List[str] = []

    for i, row in enumerate(rows, start=2):
        turma = get_col(row, "turma", "Turma") or ""
        disciplina = get_col(row, "disciplina", "Disciplina") or ""
        if not turma or not disciplina:
            errors.append(f"Linha {i}: turma e disciplina obrigatórias")
            continue

        # Year level
        ano_raw = get_col(row, "ano", "Ano")
        try:
            year_level = int(ano_raw) if ano_raw else 5
        except ValueError:
            year_level = 5

        # Hours per week — accept decimal comma or dot
        horas_raw = get_col(row, "horas semana", "horas_semana", "horas", "Horas semana", "Horas") or "2"
        horas_raw = horas_raw.replace(",", ".")
        try:
            hours_per_week = float(horas_raw)
        except ValueError:
            hours_per_week = 2.0

        # Teacher name (optional)
        professor = get_col(row, "professor", "Professor") or None

        # Articulado flag
        articulado_raw = (get_col(row, "articulado", "Articulado") or "").lower().strip()
        is_articulated = articulado_raw in ("sim", "s", "yes", "y", "1", "true")

        # ── Find or create Class ──────────────────────────────────────────────
        cls = db.query(Class).filter(
            Class.school_id == school_id,
            Class.academic_year_id == academic_year_id,
            Class.name == turma,
        ).first()
        if not cls:
            cls = Class(
                school_id=school_id,
                academic_year_id=academic_year_id,
                name=turma,
                year_level=year_level,
                num_students=25,
            )
            db.add(cls)
            db.flush()
            stats["classes"] += 1

        # ── Find or create Subject ────────────────────────────────────────────
        subj = db.query(Subject).filter(
            Subject.cluster_id == cluster_id,
            Subject.name == disciplina,
        ).first()
        if not subj:
            subj = Subject(cluster_id=cluster_id, name=disciplina)
            db.add(subj)
            db.flush()
            stats["subjects"] += 1

        # ── Find or create Teacher ────────────────────────────────────────────
        teacher = None
        if professor:
            teacher = db.query(Teacher).filter(
                Teacher.cluster_id == cluster_id,
                Teacher.name == professor,
            ).first()
            if not teacher:
                teacher = Teacher(cluster_id=cluster_id, name=professor)
                db.add(teacher)
                db.flush()
                stats["teachers"] += 1

            # Link teacher → subject
            if not db.query(TeacherSubject).filter(
                TeacherSubject.teacher_id == teacher.id,
                TeacherSubject.subject_id == subj.id,
            ).first():
                db.add(TeacherSubject(teacher_id=teacher.id, subject_id=subj.id))

            # Link teacher → school (for this academic year)
            if not db.query(TeacherSchoolAssignment).filter(
                TeacherSchoolAssignment.teacher_id == teacher.id,
                TeacherSchoolAssignment.school_id == school_id,
                TeacherSchoolAssignment.academic_year_id == academic_year_id,
            ).first():
                db.add(TeacherSchoolAssignment(
                    teacher_id=teacher.id,
                    school_id=school_id,
                    academic_year_id=academic_year_id,
                    travel_time_minutes=0,
                ))

        # ── Find or create CurriculumEntry ────────────────────────────────────
        existing_entry = db.query(CurriculumEntry).filter(
            CurriculumEntry.class_id == cls.id,
            CurriculumEntry.subject_id == subj.id,
        ).first()
        if existing_entry:
            stats["skipped"] += 1
            continue

        split_count = max(1, round(hours_per_week))
        entry = CurriculumEntry(
            class_id=cls.id,
            subject_id=subj.id,
            hours_per_week=hours_per_week,
            is_split=split_count > 1 or is_articulated,
            split_count=split_count,
            consecutive_pairs=0,
            is_semestral=False,
        )
        db.add(entry)
        stats["entries"] += 1

    db.commit()
    return {
        "created": stats["entries"],
        "skipped": stats["skipped"],
        "new_classes": stats["classes"],
        "new_subjects": stats["subjects"],
        "new_teachers": stats["teachers"],
        "errors": errors,
    }


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
