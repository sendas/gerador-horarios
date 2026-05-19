import csv
import io
import os
import json
import base64
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
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
        first_line = text.split('\n')[0] if text else ''
        delimiter = ';' if first_line.count(';') > first_line.count(',') else ','
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
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


def _resolve_school_id(turma: str, school_id: Optional[int], schools_by_code: Dict[str, Any]) -> Optional[int]:
    if school_id is not None:
        return school_id
    parts = turma.strip().split()
    if len(parts) >= 2:
        prefix = parts[-1].upper()
        school = schools_by_code.get(prefix)
        if school:
            return school.id
    return None


def _process_curriculum_row(
    db: Session,
    row: Dict[str, Any],
    row_num: int,
    cluster_id: int,
    school_id: Optional[int],
    academic_year_id: int,
    stats: Dict[str, int],
    errors: List[str],
    schools_by_code: Optional[Dict[str, Any]] = None,
) -> None:
    turma = get_col(row, "turma", "Turma") or ""
    disciplina = get_col(row, "disciplina", "Disciplina") or ""
    if not turma or not disciplina:
        errors.append(f"Linha {row_num}: turma e disciplina obrigatórias")
        return

    effective_school_id = _resolve_school_id(turma, school_id, schools_by_code or {})
    if effective_school_id is None:
        errors.append(f"Linha {row_num}: escola não encontrada para turma '{turma}' (verifique o código da escola no agrupamento)")
        return

    ano_raw = get_col(row, "ano", "Ano")
    try:
        year_level = int(ano_raw) if ano_raw else 5
    except ValueError:
        year_level = 5

    horas_raw = get_col(row, "horas semana", "horas_semana", "horas", "Horas semana", "Horas") or "2"
    horas_raw = horas_raw.replace(",", ".")
    try:
        hours_per_week = float(horas_raw)
    except ValueError:
        hours_per_week = 2.0

    professor_raw = get_col(row, "professor", "Professor") or None
    # When no professor given, create a placeholder so the solver can proceed
    if not professor_raw:
        abbrev = ''.join(c for c in disciplina.upper() if c.isalpha())[:8]
        professor = f"PROF_{abbrev}_1"
    else:
        professor = professor_raw

    articulado_raw = (get_col(row, "articulado", "Articulado") or "").strip()
    articulado_lower = articulado_raw.lower()
    is_articulated = articulado_lower in ("sim", "s", "yes", "y", "1", "true")
    articulado_note = articulado_raw if articulado_raw and not is_articulated else None

    cls = db.query(Class).filter(
        Class.school_id == effective_school_id,
        Class.academic_year_id == academic_year_id,
        Class.name == turma,
    ).first()
    if not cls:
        cls = Class(
            school_id=effective_school_id,
            academic_year_id=academic_year_id,
            name=turma,
            year_level=year_level,
            num_students=25,
            notes=articulado_note,
        )
        db.add(cls)
        db.flush()
        stats["new_classes"] += 1
    elif articulado_note and not cls.notes:
        cls.notes = articulado_note

    subj = db.query(Subject).filter(
        Subject.cluster_id == cluster_id,
        Subject.name == disciplina,
    ).first()
    if not subj:
        subj = Subject(
            cluster_id=cluster_id,
            name=disciplina,
            can_exempt_articulado=is_articulated,
        )
        db.add(subj)
        db.flush()
        stats["new_subjects"] += 1
    elif is_articulated and not subj.can_exempt_articulado:
        subj.can_exempt_articulado = True

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
            stats["new_teachers"] += 1

        if not db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == teacher.id,
            TeacherSubject.subject_id == subj.id,
        ).first():
            db.add(TeacherSubject(teacher_id=teacher.id, subject_id=subj.id))

        if not db.query(TeacherSchoolAssignment).filter(
            TeacherSchoolAssignment.teacher_id == teacher.id,
            TeacherSchoolAssignment.school_id == effective_school_id,
            TeacherSchoolAssignment.academic_year_id == academic_year_id,
        ).first():
            db.add(TeacherSchoolAssignment(
                teacher_id=teacher.id,
                school_id=effective_school_id,
                academic_year_id=academic_year_id,
                travel_time_minutes=0,
            ))

    existing_entry = db.query(CurriculumEntry).filter(
        CurriculumEntry.class_id == cls.id,
        CurriculumEntry.subject_id == subj.id,
    ).first()
    if existing_entry:
        if teacher and not existing_entry.teacher_id:
            existing_entry.teacher_id = teacher.id
        stats["skipped"] += 1
        return

    split_count = max(1, round(hours_per_week))
    entry = CurriculumEntry(
        class_id=cls.id,
        subject_id=subj.id,
        hours_per_week=hours_per_week,
        is_split=split_count > 1,
        split_count=split_count,
        consecutive_pairs=0,
        is_semestral=False,
        teacher_id=teacher.id if teacher else None,
    )
    db.add(entry)
    stats["created"] += 1


@router.post("/teaching-components")
def import_teaching_components(
    file: UploadFile = File(...),
    cluster_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Import/update teaching component hours for teachers from CSV/XLSX.
    Columns: professor (or nome), comp. letiva (or teaching_component).
    Matches teachers by name within the cluster and updates their teaching_component.
    """
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Agrupamento não encontrado")

    rows = parse_upload(file)
    updated = 0
    not_found = 0
    errors: List[str] = []

    for i, row in enumerate(rows, start=2):
        name = get_col(row, "professor", "nome", "Professor", "Nome", "name")
        if not name:
            errors.append(f"Linha {i}: nome do professor em falta")
            continue

        comp_raw = get_col(
            row,
            "comp. letiva", "comp_letiva", "componente letiva", "componente_letiva",
            "teaching_component", "Comp. Letiva", "Componente Letiva",
        )
        if comp_raw is None:
            errors.append(f"Linha {i}: componente letiva em falta")
            continue

        try:
            comp = int(float(str(comp_raw).replace(",", ".")))
        except (ValueError, TypeError):
            errors.append(f"Linha {i}: valor inválido para componente letiva: {comp_raw}")
            continue

        teacher = db.query(Teacher).filter(
            Teacher.cluster_id == cluster_id,
            Teacher.name == name,
        ).first()

        if not teacher:
            not_found += 1
            errors.append(f"Linha {i}: professor '{name}' não encontrado no agrupamento")
            continue

        teacher.teaching_component = comp
        updated += 1

    db.commit()
    return {"updated": updated, "not_found": not_found, "errors": errors}


@router.post("/curriculum/stream")
def import_curriculum_stream(
    file: UploadFile = File(...),
    cluster_id: int = Form(...),
    school_id: Optional[int] = Form(default=None),
    academic_year_id: int = Form(...),
    filter_classes: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Stream curriculum import progress as NDJSON. Commits each row individually for resumability.
    school_id is optional: if omitted, the school is resolved per row from the class name suffix
    (e.g. '5 A PN' matches a school with code 'PN' in the cluster).
    """
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Agrupamento não encontrado")

    if school_id is not None:
        school = db.query(School).filter(School.id == school_id).first()
        if not school:
            raise HTTPException(status_code=404, detail="Escola não encontrada")

    # Pre-load schools by code so each row can auto-resolve its school from the class name suffix
    schools_by_code: Dict[str, Any] = {}
    if school_id is None:
        for s in db.query(School).filter(School.cluster_id == cluster_id).all():
            if s.code:
                schools_by_code[s.code.upper()] = s

    rows = parse_upload(file)

    if filter_classes.strip():
        try:
            allowed = set(json.loads(filter_classes))
            rows = [r for r in rows if (get_col(r, "turma", "Turma") or "") in allowed]
        except (json.JSONDecodeError, TypeError):
            pass

    total = len(rows)

    def generate():
        stats: Dict[str, int] = dict(created=0, skipped=0, new_classes=0, new_subjects=0, new_teachers=0)
        errors: List[str] = []
        try:
            for i, row in enumerate(rows):
                row_num = i + 2
                try:
                    _process_curriculum_row(db, row, row_num, cluster_id, school_id, academic_year_id, stats, errors, schools_by_code)
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    errors.append(f"Linha {row_num}: {str(exc)[:120]}")

                yield json.dumps({
                    "processed": i + 1,
                    "total": total,
                    "created": stats["created"],
                    "skipped": stats["skipped"],
                    "new_classes": stats["new_classes"],
                    "new_subjects": stats["new_subjects"],
                    "new_teachers": stats["new_teachers"],
                    "errors": errors[-50:],
                }) + "\n"

            yield json.dumps({
                "done": True,
                "processed": total,
                "total": total,
                "created": stats["created"],
                "skipped": stats["skipped"],
                "new_classes": stats["new_classes"],
                "new_subjects": stats["new_subjects"],
                "new_teachers": stats["new_teachers"],
                "errors": errors,
            }) + "\n"
        except Exception as fatal:
            db.rollback()
            yield json.dumps({
                "done": True,
                "error": f"Erro interno: {str(fatal)[:200]}",
                "processed": 0,
                "total": total,
                "created": stats["created"],
                "skipped": stats["skipped"],
                "new_classes": stats["new_classes"],
                "new_subjects": stats["new_subjects"],
                "new_teachers": stats["new_teachers"],
                "errors": errors + [f"Erro fatal: {str(fatal)[:200]}"],
            }) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no"},
    )


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

        # Articulado field:
        #   empty              → sem articulado
        #   "sim"/"s"/… → can_exempt_articulado = True na disciplina
        #   outro valor        → observação importante; guardada em cls.notes
        articulado_raw = (get_col(row, "articulado", "Articulado") or "").strip()
        articulado_lower = articulado_raw.lower()
        is_articulated = articulado_lower in ("sim", "s", "yes", "y", "1", "true")
        articulado_note = articulado_raw if articulado_raw and not is_articulated else None

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
                notes=articulado_note,
            )
            db.add(cls)
            db.flush()
            stats["classes"] += 1
        elif articulado_note and not cls.notes:
            # Only fill notes if not already set and articulado has a non-"sim" value
            cls.notes = articulado_note

        # ── Find or create Subject ────────────────────────────────────────────
        subj = db.query(Subject).filter(
            Subject.cluster_id == cluster_id,
            Subject.name == disciplina,
        ).first()
        if not subj:
            subj = Subject(
                cluster_id=cluster_id,
                name=disciplina,
                can_exempt_articulado=is_articulated,
            )
            db.add(subj)
            db.flush()
            stats["subjects"] += 1
        elif is_articulated and not subj.can_exempt_articulado:
            subj.can_exempt_articulado = True

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
            if teacher and not existing_entry.teacher_id:
                existing_entry.teacher_id = teacher.id
            stats["skipped"] += 1
            continue

        split_count = max(1, round(hours_per_week))
        entry = CurriculumEntry(
            class_id=cls.id,
            subject_id=subj.id,
            hours_per_week=hours_per_week,
            is_split=split_count > 1,
            split_count=split_count,
            consecutive_pairs=0,
            is_semestral=False,
            teacher_id=teacher.id if teacher else None,
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
