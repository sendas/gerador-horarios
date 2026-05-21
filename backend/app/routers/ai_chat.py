import os
import json
import threading
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    Cluster, School, AcademicYear, Timetable, Teacher, Class,
    ScheduledLesson, CurriculumEntry, NonTeachingAssignment,
)
from app.auth import get_current_user

router = APIRouter(prefix="/ai", tags=["ai"])

# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    academic_year_id: Optional[int] = None
    cluster_id: Optional[int] = None

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM = """És um assistente inteligente integrado no Sinaptik, um sistema de gestão e geração \
automática de horários escolares português.

Ajudas administradores e diretores a:
- Consultar o estado de professores, turmas e horários
- Interpretar erros de geração (INFEASIBLE, UNKNOWN, timeout)
- Gerir componentes letivas e reduções do Artigo 79.º ECD
- Iniciar gerações de horários com filtros específicos
- Analisar distribuição de serviço

Responde sempre em português europeu, de forma clara e direta.
Usa sempre as ferramentas para obter dados reais antes de responder — nunca inventes valores.
Formata respostas com markdown: listas, negrito para valores chave.
Quando há erros de geração, explica a causa provável e sugere ações concretas."""

# ── Tool definitions ──────────────────────────────────────────────────────────

_TOOLS = [
    {
        "name": "obter_contexto",
        "description": (
            "Obtém o contexto geral do sistema: agrupamentos, ano letivo ativo, escolas e "
            "horários recentes. Chama sempre isto primeiro se não souberes o contexto."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "listar_professores",
        "description": (
            "Lista professores de um agrupamento com componente letiva, redução de horas e, "
            "opcionalmente, horas já marcadas num horário."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "integer", "description": "ID do agrupamento"},
                "timetable_id": {"type": "integer", "description": "ID do horário (opcional)"},
            },
            "required": ["cluster_id"],
        },
    },
    {
        "name": "listar_turmas",
        "description": (
            "Lista turmas de um ano letivo com escola, ano de escolaridade e cobertura curricular."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo"},
                "school_id": {"type": "integer", "description": "Filtrar por escola (opcional)"},
                "year_level": {"type": "integer", "description": "Filtrar por ano (opcional)"},
            },
            "required": ["academic_year_id"],
        },
    },
    {
        "name": "ver_estado_horario",
        "description": (
            "Obtém o estado atual de um horário: status, resultado do solver, número de aulas "
            "marcadas e as últimas linhas do log de geração."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "timetable_id": {"type": "integer", "description": "ID do horário"},
            },
            "required": ["timetable_id"],
        },
    },
    {
        "name": "ver_distribuicao_servico",
        "description": (
            "Mostra a distribuição de serviço dos professores: componente letiva vs horas marcadas, "
            "identificando professores em défice, excesso ou sem componente definida."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo"},
                "timetable_id": {"type": "integer", "description": "ID do horário (opcional)"},
            },
            "required": ["academic_year_id"],
        },
    },
    {
        "name": "iniciar_geracao",
        "description": (
            "Inicia a geração de um horário em segundo plano. Pode filtrar por turmas, escolas "
            "ou anos de escolaridade. Usa ver_estado_horario para acompanhar o progresso."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "timetable_id": {"type": "integer", "description": "ID do horário"},
                "year_levels": {
                    "type": "array", "items": {"type": "integer"},
                    "description": "Anos de escolaridade a gerar (ex: [7,8,9]). Omitir = todos.",
                },
                "school_ids": {
                    "type": "array", "items": {"type": "integer"},
                    "description": "IDs de escolas a incluir. Omitir = todas.",
                },
                "class_ids": {
                    "type": "array", "items": {"type": "integer"},
                    "description": "IDs de turmas específicas. Sobrepõe-se aos outros filtros.",
                },
                "max_time_seconds": {
                    "type": "integer",
                    "description": "Tempo máximo em segundos (padrão: 300).",
                },
            },
            "required": ["timetable_id"],
        },
    },
    {
        "name": "definir_componentes_letivos",
        "description": (
            "Define a componente letiva (horas semanais) para todos os professores de um "
            "agrupamento, com opção de aplicar reduções automáticas do Art. 79.º ECD por idade."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "integer", "description": "ID do agrupamento"},
                "base_component": {"type": "integer", "description": "Componente base em horas (ex: 22)"},
                "apply_art79": {
                    "type": "boolean",
                    "description": "Aplicar reduções Art. 79.º: 50-54a→-1h, 55-59a→-2h, ≥60a→-3h",
                },
            },
            "required": ["cluster_id", "base_component"],
        },
    },
]

# ── Tool implementations ──────────────────────────────────────────────────────

def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _tool_obter_contexto(db: Session) -> str:
    clusters = db.query(Cluster).all()
    active_year = db.query(AcademicYear).filter(AcademicYear.is_active.is_(True)).first()

    result: dict = {
        "agrupamentos": [{"id": c.id, "nome": c.name} for c in clusters],
        "ano_letivo_ativo": None,
        "escolas": [],
        "horarios_recentes": [],
    }

    if active_year:
        result["ano_letivo_ativo"] = {
            "id": active_year.id,
            "nome": active_year.name,
            "cluster_id": active_year.cluster_id,
        }
        schools = db.query(School).filter(School.cluster_id == active_year.cluster_id).all()
        result["escolas"] = [{"id": s.id, "nome": s.name, "codigo": s.code} for s in schools]
        timetables = (
            db.query(Timetable)
            .filter(Timetable.academic_year_id == active_year.id)
            .order_by(Timetable.created_at.desc())
            .limit(5)
            .all()
        )
        result["horarios_recentes"] = [
            {"id": t.id, "nome": t.name, "status": t.status, "solver_status": t.solver_status}
            for t in timetables
        ]

    return _j(result)


def _tool_listar_professores(db: Session, cluster_id: int, timetable_id: int = None) -> str:
    teachers = (
        db.query(Teacher)
        .filter(Teacher.cluster_id == cluster_id)
        .order_by(Teacher.name)
        .all()
    )

    scheduled: dict = {}
    if timetable_id:
        for lesson in db.query(ScheduledLesson).filter(ScheduledLesson.timetable_id == timetable_id).all():
            if lesson.teacher_id:
                scheduled[lesson.teacher_id] = scheduled.get(lesson.teacher_id, 0) + 1

    rows = []
    for t in teachers:
        row: dict = {
            "id": t.id,
            "nome": t.name,
            "componente_letiva": t.teaching_component,
            "reducao_horas": t.credit_hours or 0,
            "data_nascimento": str(t.birth_date) if t.birth_date else None,
        }
        if timetable_id is not None:
            row["horas_marcadas"] = scheduled.get(t.id, 0)
        rows.append(row)

    return _j({"professores": rows, "total": len(rows)})


def _tool_listar_turmas(
    db: Session, academic_year_id: int, school_id: int = None, year_level: int = None
) -> str:
    q = db.query(Class).filter(Class.academic_year_id == academic_year_id)
    if school_id:
        q = q.filter(Class.school_id == school_id)
    if year_level:
        q = q.filter(Class.year_level == year_level)
    classes = q.order_by(Class.year_level, Class.name).all()

    school_cache: dict = {}

    def school_name(sid):
        if sid not in school_cache:
            s = db.query(School).filter(School.id == sid).first()
            school_cache[sid] = s.name if s else None
        return school_cache[sid]

    rows = []
    for c in classes:
        total = db.query(CurriculumEntry).filter(CurriculumEntry.class_id == c.id).count()
        with_teacher = (
            db.query(CurriculumEntry)
            .filter(CurriculumEntry.class_id == c.id, CurriculumEntry.teacher_id.isnot(None))
            .count()
        )
        rows.append({
            "id": c.id,
            "nome": c.name,
            "ano": c.year_level,
            "escola": school_name(c.school_id),
            "escola_id": c.school_id,
            "entradas_curriculo": total,
            "entradas_com_professor": with_teacher,
            "cobertura_pct": round(with_teacher / total * 100) if total else 0,
        })

    return _j({"turmas": rows, "total": len(rows)})


def _tool_ver_estado_horario(db: Session, timetable_id: int) -> str:
    t = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not t:
        return _j({"erro": f"Horário {timetable_id} não encontrado"})

    log_lines: list = []
    if t.generation_log:
        lines = t.generation_log.strip().split("\n")
        log_lines = lines[-60:]

    lesson_count = (
        db.query(ScheduledLesson).filter(ScheduledLesson.timetable_id == timetable_id).count()
    )

    return _j({
        "id": t.id,
        "nome": t.name,
        "status": t.status,
        "solver_status": t.solver_status,
        "aulas_marcadas": lesson_count,
        "ultimo_log": log_lines,
        "atualizado_em": t.updated_at,
    })


def _tool_ver_distribuicao(db: Session, academic_year_id: int, timetable_id: int = None) -> str:
    year = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    if not year:
        return _j({"erro": "Ano letivo não encontrado"})

    teachers = (
        db.query(Teacher)
        .filter(Teacher.cluster_id == year.cluster_id)
        .order_by(Teacher.name)
        .all()
    )

    scheduled: dict = {}
    if timetable_id:
        for lesson in db.query(ScheduledLesson).filter(ScheduledLesson.timetable_id == timetable_id).all():
            if lesson.teacher_id:
                scheduled[lesson.teacher_id] = scheduled.get(lesson.teacher_id, 0) + 1

    nt_hours: dict = {}
    for nt in db.query(NonTeachingAssignment).filter(
        NonTeachingAssignment.academic_year_id == academic_year_id
    ).all():
        nt_hours[nt.teacher_id] = nt_hours.get(nt.teacher_id, 0) + (nt.hours_per_week or 0)

    rows = []
    for t in teachers:
        comp = t.teaching_component
        sched = scheduled.get(t.id, 0)
        nt = nt_hours.get(t.id, 0)
        if comp is None:
            status = "sem_componente"
        elif sched > comp:
            status = "excesso"
        elif sched >= comp * 0.9:
            status = "ok"
        else:
            status = "deficit"
        rows.append({
            "id": t.id,
            "nome": t.name,
            "componente": comp,
            "horas_marcadas": sched,
            "horas_nao_letivas": nt,
            "status": status if timetable_id else "sem_horario",
        })

    resumo = {
        "total": len(rows),
        "sem_componente": sum(1 for r in rows if r["status"] == "sem_componente"),
        "ok": sum(1 for r in rows if r["status"] == "ok"),
        "deficit": sum(1 for r in rows if r["status"] == "deficit"),
        "excesso": sum(1 for r in rows if r["status"] == "excesso"),
    }
    return _j({"professores": rows, "resumo": resumo})


def _tool_iniciar_geracao(
    db: Session,
    timetable_id: int,
    year_levels: list = None,
    school_ids: list = None,
    class_ids: list = None,
    max_time_seconds: int = 300,
) -> str:
    t = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not t:
        return _j({"erro": f"Horário {timetable_id} não encontrado"})
    if t.status == "generating":
        return _j({"erro": "Horário já está a ser gerado. Aguarda o fim antes de reiniciar."})

    t.status = "generating"
    t.updated_at = datetime.utcnow()
    db.commit()

    options = {
        "year_levels": year_levels,
        "school_ids": school_ids,
        "class_ids": class_ids,
        "max_time_seconds": max_time_seconds,
        "no_student_gaps": True,
        "minimize_teacher_gaps": True,
        "teacher_gap_weight": 10,
        "no_same_subject_twice_per_day": True,
        "distribute_subjects_weight": 5,
        "students_start_slot_1": True,
        "no_pe_after_lunch": True,
        "lunch_after_slot": 4,
    }

    from app.scheduler.engine import generate_timetable as _run_solver

    def _bg():
        _run_solver(timetable_id, options)

    threading.Thread(target=_bg, daemon=True).start()

    parts = []
    if class_ids:
        parts.append(f"{len(class_ids)} turma(s) específica(s)")
    elif year_levels:
        parts.append(f"anos {', '.join(str(y) for y in year_levels)}")
    elif school_ids:
        parts.append(f"{len(school_ids)} escola(s)")
    else:
        parts.append("todas as turmas")

    return _j({
        "sucesso": True,
        "mensagem": f"Geração iniciada para '{t.name}' ({', '.join(parts)})",
        "timetable_id": timetable_id,
        "nota": "Usa ver_estado_horario para acompanhar o progresso.",
    })


def _tool_definir_componentes(
    db: Session, cluster_id: int, base_component: int, apply_art79: bool = False
) -> str:
    teachers = db.query(Teacher).filter(Teacher.cluster_id == cluster_id).all()
    today = datetime.today().date()
    updated = 0

    for t in teachers:
        reduction = 0
        if apply_art79 and t.birth_date:
            age = (today - t.birth_date).days // 365
            if age >= 60:
                reduction = 3
            elif age >= 55:
                reduction = 2
            elif age >= 50:
                reduction = 1
        t.teaching_component = base_component - reduction
        if reduction > 0:
            t.credit_hours = reduction
        updated += 1

    db.commit()
    return _j({
        "sucesso": True,
        "professores_atualizados": updated,
        "componente_base": base_component,
        "art79_aplicado": apply_art79,
    })


def _execute_tool(name: str, inp: dict, db: Session) -> str:
    try:
        if name == "obter_contexto":
            return _tool_obter_contexto(db)
        if name == "listar_professores":
            return _tool_listar_professores(db, **inp)
        if name == "listar_turmas":
            return _tool_listar_turmas(db, **inp)
        if name == "ver_estado_horario":
            return _tool_ver_estado_horario(db, **inp)
        if name == "ver_distribuicao_servico":
            return _tool_ver_distribuicao(db, **inp)
        if name == "iniciar_geracao":
            return _tool_iniciar_geracao(db, **inp)
        if name == "definir_componentes_letivos":
            return _tool_definir_componentes(db, **inp)
        return _j({"erro": f"Ferramenta desconhecida: {name}"})
    except Exception as exc:
        return _j({"erro": str(exc)})


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY não configurada. Adiciona a variável de ambiente ao servidor.",
        )

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    messages: list = [{"role": m.role, "content": m.content} for m in request.messages]
    tools_called: list = []

    for _ in range(10):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=_SYSTEM,
            tools=_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = next((b.text for b in response.content if hasattr(b, "text")), "")
            return {"response": text, "tools_called": tools_called}

        if response.stop_reason == "tool_use":
            # Build assistant turn from response content blocks
            assistant_content = []
            tool_results = []

            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                    tools_called.append(block.name)
                    result = _execute_tool(block.name, block.input, db)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return {"response": "Não foi possível processar o pedido.", "tools_called": tools_called}
