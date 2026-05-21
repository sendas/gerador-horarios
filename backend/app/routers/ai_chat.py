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
    ScheduledLesson, CurriculumEntry, NonTeachingAssignment, NonTeachingType,
    SchedulingRules, TimeSlotConfig, Subject, TeacherSchoolAssignment,
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
- Criar, iniciar e diagnosticar gerações de horários
- Analisar e editar distribuição de serviço e horários individuais

Responde sempre em português europeu, de forma clara e direta.
Usa SEMPRE as ferramentas para obter dados reais antes de responder — nunca inventes IDs ou valores.
Quando precisares de um ID (professor, turma, horário), usa as ferramentas de listagem primeiro.
Formata respostas com markdown: listas, negrito para valores chave, tabelas quando adequado.
Quando há erros de geração, explica a causa provável e sugere ações concretas."""

# ── Tool definitions ──────────────────────────────────────────────────────────

_TOOLS = [
    # ── Contexto ──────────────────────────────────────────────────────────────
    {
        "name": "obter_contexto",
        "description": (
            "Obtém o contexto geral: agrupamentos, ano letivo ativo, escolas e horários recentes. "
            "Chama sempre isto primeiro se não souberes o contexto."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # ── Professores ───────────────────────────────────────────────────────────
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
                "timetable_id": {"type": "integer", "description": "ID do horário para incluir horas marcadas (opcional)"},
            },
            "required": ["cluster_id"],
        },
    },
    {
        "name": "atualizar_professor",
        "description": (
            "Atualiza dados de um professor específico: componente letiva, data de nascimento, "
            "horas de redução ou máximo de aulas por dia. Usa listar_professores para obter o ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "teacher_id": {"type": "integer", "description": "ID do professor"},
                "teaching_component": {"type": "integer", "description": "Componente letiva em horas/semana"},
                "credit_hours": {"type": "integer", "description": "Horas de redução (Art. 79.º ou outro)"},
                "birth_date": {"type": "string", "description": "Data de nascimento em formato YYYY-MM-DD"},
                "max_daily_lessons": {"type": "integer", "description": "Máximo de aulas por dia"},
            },
            "required": ["teacher_id"],
        },
    },
    # ── Turmas ────────────────────────────────────────────────────────────────
    {
        "name": "listar_turmas",
        "description": "Lista turmas de um ano letivo com escola, ano de escolaridade e cobertura curricular.",
        "input_schema": {
            "type": "object",
            "properties": {
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo"},
                "school_id": {"type": "integer", "description": "Filtrar por escola (opcional)"},
                "year_level": {"type": "integer", "description": "Filtrar por ano de escolaridade (opcional)"},
            },
            "required": ["academic_year_id"],
        },
    },
    # ── Horários ──────────────────────────────────────────────────────────────
    {
        "name": "ver_estado_horario",
        "description": (
            "Obtém o estado de um horário: status, resultado do solver, aulas marcadas "
            "e as últimas linhas do log de geração."
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
        "name": "ver_preflight_horario",
        "description": (
            "Verifica se um horário pode ser gerado: lista erros bloqueantes, avisos e "
            "resumo por ano de escolaridade. Útil antes de iniciar geração."
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
        "name": "criar_horario",
        "description": "Cria um novo horário (rascunho) para um ano letivo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo"},
                "nome": {"type": "string", "description": "Nome do horário (ex: 'Horário 2025/26 v2')"},
            },
            "required": ["academic_year_id", "nome"],
        },
    },
    {
        "name": "iniciar_geracao",
        "description": (
            "Inicia a geração de um horário em segundo plano com filtros opcionais. "
            "Usa ver_estado_horario para acompanhar o progresso."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "timetable_id": {"type": "integer", "description": "ID do horário"},
                "year_levels": {
                    "type": "array", "items": {"type": "integer"},
                    "description": "Anos de escolaridade (ex: [7,8,9]). Omitir = todos.",
                },
                "school_ids": {
                    "type": "array", "items": {"type": "integer"},
                    "description": "IDs de escolas. Omitir = todas.",
                },
                "class_ids": {
                    "type": "array", "items": {"type": "integer"},
                    "description": "IDs de turmas específicas (sobrepõe-se aos outros filtros).",
                },
                "max_time_seconds": {
                    "type": "integer",
                    "description": "Limite de tempo em segundos (padrão: 300).",
                },
            },
            "required": ["timetable_id"],
        },
    },
    {
        "name": "ver_horario_professor",
        "description": (
            "Mostra o horário semanal de um professor num horário gerado: "
            "aulas por dia e slot com turma e disciplina. "
            "Usa listar_professores para obter o ID do professor."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "timetable_id": {"type": "integer", "description": "ID do horário"},
                "teacher_id": {"type": "integer", "description": "ID do professor"},
            },
            "required": ["timetable_id", "teacher_id"],
        },
    },
    {
        "name": "ver_horario_turma",
        "description": (
            "Mostra o horário semanal de uma turma num horário gerado: "
            "aulas por dia e slot com professor e disciplina. "
            "Usa listar_turmas para obter o ID da turma."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "timetable_id": {"type": "integer", "description": "ID do horário"},
                "class_id": {"type": "integer", "description": "ID da turma"},
            },
            "required": ["timetable_id", "class_id"],
        },
    },
    {
        "name": "mover_aula",
        "description": (
            "Move uma aula para outro dia e slot. Usa ver_horario_turma ou ver_horario_professor "
            "para obter o lesson_id. Dias: 0=Segunda, 1=Terça, 2=Quarta, 3=Quinta, 4=Sexta."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "timetable_id": {"type": "integer", "description": "ID do horário"},
                "lesson_id": {"type": "integer", "description": "ID da aula a mover"},
                "novo_dia": {"type": "integer", "description": "Novo dia (0=Seg, 1=Ter, 2=Qua, 3=Qui, 4=Sex)"},
                "novo_slot": {"type": "integer", "description": "Novo número do slot/tempo"},
            },
            "required": ["timetable_id", "lesson_id", "novo_dia", "novo_slot"],
        },
    },
    # ── Serviço ───────────────────────────────────────────────────────────────
    {
        "name": "ver_distribuicao_servico",
        "description": (
            "Distribuição de serviço dos professores: componente letiva vs horas marcadas, "
            "identificando défice, excesso ou sem componente definida."
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
        "name": "definir_componentes_letivos",
        "description": (
            "Define a componente letiva para todos os professores de um agrupamento, "
            "com opção de aplicar reduções automáticas do Art. 79.º ECD por idade."
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
    {
        "name": "listar_servico_nao_letivo",
        "description": (
            "Lista o serviço não letivo atribuído aos professores num ano letivo: "
            "tipo de serviço, dia, slot e escola."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo"},
                "teacher_id": {"type": "integer", "description": "Filtrar por professor (opcional)"},
            },
            "required": ["academic_year_id"],
        },
    },
    # ── Regras ────────────────────────────────────────────────────────────────
    {
        "name": "ver_regras_horario",
        "description": (
            "Mostra as regras de horário configuradas para um agrupamento: "
            "máximo de aulas por dia, aulas consecutivas, restrições de gaps, etc. "
            "Útil para diagnosticar erros INFEASIBLE."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "integer", "description": "ID do agrupamento"},
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo (opcional)"},
            },
            "required": ["cluster_id"],
        },
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

_DAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]

def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)

def _day_name(d: int) -> str:
    return _DAYS[d] if 0 <= d < len(_DAYS) else str(d)

# ── Tool implementations ──────────────────────────────────────────────────────

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
            "id": active_year.id, "nome": active_year.name, "cluster_id": active_year.cluster_id,
        }
        schools = db.query(School).filter(School.cluster_id == active_year.cluster_id).all()
        result["escolas"] = [{"id": s.id, "nome": s.name, "codigo": s.code} for s in schools]
        timetables = (
            db.query(Timetable)
            .filter(Timetable.academic_year_id == active_year.id)
            .order_by(Timetable.created_at.desc()).limit(5).all()
        )
        result["horarios_recentes"] = [
            {"id": t.id, "nome": t.name, "status": t.status, "solver_status": t.solver_status}
            for t in timetables
        ]
    return _j(result)


def _tool_listar_professores(db: Session, cluster_id: int, timetable_id: int = None) -> str:
    teachers = db.query(Teacher).filter(Teacher.cluster_id == cluster_id).order_by(Teacher.name).all()
    scheduled: dict = {}
    if timetable_id:
        for lesson in db.query(ScheduledLesson).filter(ScheduledLesson.timetable_id == timetable_id).all():
            if lesson.teacher_id:
                scheduled[lesson.teacher_id] = scheduled.get(lesson.teacher_id, 0) + 1
    rows = []
    for t in teachers:
        row: dict = {
            "id": t.id, "nome": t.name,
            "componente_letiva": t.teaching_component,
            "reducao_horas": t.credit_hours or 0,
            "data_nascimento": str(t.birth_date) if t.birth_date else None,
            "max_aulas_dia": t.max_daily_lessons,
        }
        if timetable_id is not None:
            row["horas_marcadas"] = scheduled.get(t.id, 0)
        rows.append(row)
    return _j({"professores": rows, "total": len(rows)})


def _tool_atualizar_professor(
    db: Session, teacher_id: int,
    teaching_component: int = None, credit_hours: int = None,
    birth_date: str = None, max_daily_lessons: int = None,
) -> str:
    t = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not t:
        return _j({"erro": f"Professor {teacher_id} não encontrado"})
    changed = []
    if teaching_component is not None:
        t.teaching_component = teaching_component; changed.append(f"componente_letiva={teaching_component}")
    if credit_hours is not None:
        t.credit_hours = credit_hours; changed.append(f"reducao_horas={credit_hours}")
    if birth_date is not None:
        from datetime import date as _date
        t.birth_date = _date.fromisoformat(birth_date); changed.append(f"data_nascimento={birth_date}")
    if max_daily_lessons is not None:
        t.max_daily_lessons = max_daily_lessons; changed.append(f"max_aulas_dia={max_daily_lessons}")
    if not changed:
        return _j({"aviso": "Nenhum campo para actualizar foi fornecido."})
    db.commit()
    return _j({"sucesso": True, "professor": t.name, "alteracoes": changed})


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
            "id": c.id, "nome": c.name, "ano": c.year_level,
            "escola": school_name(c.school_id), "escola_id": c.school_id,
            "entradas_curriculo": total, "entradas_com_professor": with_teacher,
            "cobertura_pct": round(with_teacher / total * 100) if total else 0,
        })
    return _j({"turmas": rows, "total": len(rows)})


def _tool_ver_estado_horario(db: Session, timetable_id: int) -> str:
    t = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not t:
        return _j({"erro": f"Horário {timetable_id} não encontrado"})
    log_lines: list = []
    if t.generation_log:
        log_lines = t.generation_log.strip().split("\n")[-60:]
    lesson_count = db.query(ScheduledLesson).filter(ScheduledLesson.timetable_id == timetable_id).count()
    return _j({
        "id": t.id, "nome": t.name, "status": t.status,
        "solver_status": t.solver_status, "aulas_marcadas": lesson_count,
        "ultimo_log": log_lines, "atualizado_em": t.updated_at,
    })


def _tool_ver_preflight(db: Session, timetable_id: int) -> str:
    t = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not t:
        return _j({"erro": f"Horário {timetable_id} não encontrado"})

    year = db.query(AcademicYear).filter(AcademicYear.id == t.academic_year_id).first()
    if not year:
        return _j({"erro": "Ano letivo não encontrado"})

    errors, warnings, info = [], [], []

    slots = db.query(TimeSlotConfig).filter(TimeSlotConfig.academic_year_id == year.id).count()
    if slots == 0:
        errors.append("Sem tempos letivos configurados → vai a /time-slots")
    else:
        info.append(f"{slots} tempos letivos configurados")

    rules = db.query(SchedulingRules).filter(
        SchedulingRules.cluster_id == year.cluster_id,
        SchedulingRules.academic_year_id == year.id,
    ).first()
    if not rules:
        warnings.append("Sem regras de horário — serão usados valores por omissão")

    school_ids = [s.id for s in db.query(School).filter(School.cluster_id == year.cluster_id).all()]
    classes = db.query(Class).filter(
        Class.academic_year_id == year.id, Class.school_id.in_(school_ids)
    ).all() if school_ids else []

    if not classes:
        errors.append("Sem turmas configuradas para este ano letivo")
    else:
        info.append(f"{len(classes)} turmas")

    all_entries = db.query(CurriculumEntry).filter(
        CurriculumEntry.class_id.in_([c.id for c in classes])
    ).all() if classes else []

    if not all_entries:
        errors.append("Sem entradas de currículo")
    else:
        with_teacher = sum(1 for e in all_entries if e.teacher_id)
        pct = round(with_teacher / len(all_entries) * 100)
        if with_teacher < len(all_entries):
            warnings.append(f"{len(all_entries) - with_teacher} entradas sem professor atribuído ({pct}% com professor)")
        else:
            info.append(f"Todos os {len(all_entries)} tempos têm professor")

    # Per year-level summary
    from collections import defaultdict
    yl: dict = defaultdict(lambda: {"turmas": 0, "entradas": 0, "com_professor": 0})
    class_by_id = {c.id: c for c in classes}
    for c in classes:
        yl[c.year_level]["turmas"] += 1
    for e in all_entries:
        cl = class_by_id.get(e.class_id)
        if cl:
            yl[cl.year_level]["entradas"] += 1
            if e.teacher_id:
                yl[cl.year_level]["com_professor"] += 1

    year_summary = [
        {"ano": y, "turmas": d["turmas"], "entradas": d["entradas"],
         "com_professor": d["com_professor"], "pronto": d["com_professor"] > 0}
        for y, d in sorted(yl.items())
    ]

    return _j({
        "pode_gerar": len(errors) == 0,
        "erros": errors, "avisos": warnings, "info": info,
        "resumo_por_ano": year_summary,
    })


def _tool_criar_horario(db: Session, academic_year_id: int, nome: str) -> str:
    year = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    if not year:
        return _j({"erro": "Ano letivo não encontrado"})
    t = Timetable(academic_year_id=academic_year_id, name=nome, status="draft")
    db.add(t)
    db.commit()
    db.refresh(t)
    return _j({"sucesso": True, "id": t.id, "nome": t.name, "status": t.status})


def _tool_iniciar_geracao(
    db: Session, timetable_id: int,
    year_levels: list = None, school_ids: list = None,
    class_ids: list = None, max_time_seconds: int = 300,
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
        "year_levels": year_levels, "school_ids": school_ids, "class_ids": class_ids,
        "max_time_seconds": max_time_seconds,
        "no_student_gaps": True, "minimize_teacher_gaps": True, "teacher_gap_weight": 10,
        "no_same_subject_twice_per_day": True, "distribute_subjects_weight": 5,
        "students_start_slot_1": True, "no_pe_after_lunch": True, "lunch_after_slot": 4,
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


def _tool_ver_horario_professor(db: Session, timetable_id: int, teacher_id: int) -> str:
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        return _j({"erro": f"Professor {teacher_id} não encontrado"})
    lessons = (
        db.query(ScheduledLesson)
        .filter(ScheduledLesson.timetable_id == timetable_id, ScheduledLesson.teacher_id == teacher_id)
        .order_by(ScheduledLesson.day_of_week, ScheduledLesson.slot_number)
        .all()
    )
    aulas = []
    for l in lessons:
        entry = l.curriculum_entry
        aulas.append({
            "lesson_id": l.id,
            "dia": _day_name(l.day_of_week), "dia_num": l.day_of_week,
            "slot": l.slot_number,
            "turma": entry.class_.name if entry and entry.class_ else None,
            "disciplina": entry.subject.name if entry and entry.subject else None,
            "sala": l.room.name if l.room else None,
        })
    return _j({"professor": teacher.name, "total_aulas": len(aulas), "aulas": aulas})


def _tool_ver_horario_turma(db: Session, timetable_id: int, class_id: int) -> str:
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        return _j({"erro": f"Turma {class_id} não encontrada"})
    entries = db.query(CurriculumEntry).filter(CurriculumEntry.class_id == class_id).all()
    entry_ids = {e.id for e in entries}
    lessons = (
        db.query(ScheduledLesson)
        .filter(
            ScheduledLesson.timetable_id == timetable_id,
            ScheduledLesson.curriculum_entry_id.in_(entry_ids),
        )
        .order_by(ScheduledLesson.day_of_week, ScheduledLesson.slot_number)
        .all()
    )
    aulas = []
    for l in lessons:
        entry = l.curriculum_entry
        aulas.append({
            "lesson_id": l.id,
            "dia": _day_name(l.day_of_week), "dia_num": l.day_of_week,
            "slot": l.slot_number,
            "disciplina": entry.subject.name if entry and entry.subject else None,
            "professor": l.teacher.name if l.teacher else None,
            "sala": l.room.name if l.room else None,
        })
    return _j({"turma": cls.name, "ano": cls.year_level, "total_aulas": len(aulas), "aulas": aulas})


def _tool_mover_aula(db: Session, timetable_id: int, lesson_id: int, novo_dia: int, novo_slot: int) -> str:
    lesson = db.query(ScheduledLesson).filter(
        ScheduledLesson.id == lesson_id, ScheduledLesson.timetable_id == timetable_id
    ).first()
    if not lesson:
        return _j({"erro": f"Aula {lesson_id} não encontrada no horário {timetable_id}"})

    # Check for conflict
    entry = lesson.curriculum_entry
    class_id = entry.class_id if entry else None
    conflito_turma = None
    conflito_prof = None

    if class_id:
        other_entries = [e.id for e in db.query(CurriculumEntry).filter(CurriculumEntry.class_id == class_id).all()]
        conflict = db.query(ScheduledLesson).filter(
            ScheduledLesson.timetable_id == timetable_id,
            ScheduledLesson.curriculum_entry_id.in_(other_entries),
            ScheduledLesson.day_of_week == novo_dia,
            ScheduledLesson.slot_number == novo_slot,
            ScheduledLesson.id != lesson_id,
        ).first()
        if conflict:
            conflito_turma = f"A turma já tem aula nesse slot ({_day_name(novo_dia)} slot {novo_slot})"

    if lesson.teacher_id:
        conflict_prof = db.query(ScheduledLesson).filter(
            ScheduledLesson.timetable_id == timetable_id,
            ScheduledLesson.teacher_id == lesson.teacher_id,
            ScheduledLesson.day_of_week == novo_dia,
            ScheduledLesson.slot_number == novo_slot,
            ScheduledLesson.id != lesson_id,
        ).first()
        if conflict_prof:
            conflito_prof = f"O professor já tem aula nesse slot ({_day_name(novo_dia)} slot {novo_slot})"

    old_dia, old_slot = lesson.day_of_week, lesson.slot_number
    lesson.day_of_week = novo_dia
    lesson.slot_number = novo_slot
    db.commit()

    result: dict = {
        "sucesso": True,
        "mensagem": f"Aula movida de {_day_name(old_dia)}/slot {old_slot} para {_day_name(novo_dia)}/slot {novo_slot}",
    }
    if conflito_turma:
        result["aviso_turma"] = conflito_turma
    if conflito_prof:
        result["aviso_professor"] = conflito_prof
    return _j(result)


def _tool_ver_distribuicao(db: Session, academic_year_id: int, timetable_id: int = None) -> str:
    year = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    if not year:
        return _j({"erro": "Ano letivo não encontrado"})
    teachers = db.query(Teacher).filter(Teacher.cluster_id == year.cluster_id).order_by(Teacher.name).all()
    scheduled: dict = {}
    if timetable_id:
        for lesson in db.query(ScheduledLesson).filter(ScheduledLesson.timetable_id == timetable_id).all():
            if lesson.teacher_id:
                scheduled[lesson.teacher_id] = scheduled.get(lesson.teacher_id, 0) + 1
    # Non-teaching: count slots per teacher (each assignment = 1 slot = 1 hour)
    nt_count: dict = {}
    for nt in db.query(NonTeachingAssignment).filter(
        NonTeachingAssignment.academic_year_id == academic_year_id
    ).all():
        nt_count[nt.teacher_id] = nt_count.get(nt.teacher_id, 0) + 1

    rows = []
    for t in teachers:
        comp = t.teaching_component
        sched = scheduled.get(t.id, 0)
        nt = nt_count.get(t.id, 0)
        if comp is None:
            status = "sem_componente"
        elif sched > comp:
            status = "excesso"
        elif sched >= comp * 0.9:
            status = "ok"
        else:
            status = "deficit"
        rows.append({
            "id": t.id, "nome": t.name, "componente": comp,
            "horas_marcadas": sched, "horas_nao_letivas": nt,
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


def _tool_definir_componentes(db: Session, cluster_id: int, base_component: int, apply_art79: bool = False) -> str:
    teachers = db.query(Teacher).filter(Teacher.cluster_id == cluster_id).all()
    today = datetime.today().date()
    updated = 0
    for t in teachers:
        reduction = 0
        if apply_art79 and t.birth_date:
            age = (today - t.birth_date).days // 365
            if age >= 60: reduction = 3
            elif age >= 55: reduction = 2
            elif age >= 50: reduction = 1
        t.teaching_component = base_component - reduction
        if reduction > 0:
            t.credit_hours = reduction
        updated += 1
    db.commit()
    return _j({
        "sucesso": True, "professores_atualizados": updated,
        "componente_base": base_component, "art79_aplicado": apply_art79,
    })


def _tool_listar_servico_nao_letivo(db: Session, academic_year_id: int, teacher_id: int = None) -> str:
    q = db.query(NonTeachingAssignment).filter(
        NonTeachingAssignment.academic_year_id == academic_year_id
    )
    if teacher_id:
        q = q.filter(NonTeachingAssignment.teacher_id == teacher_id)
    assignments = q.all()

    rows = []
    for a in assignments:
        tipo = db.query(NonTeachingType).filter(NonTeachingType.id == a.non_teaching_type_id).first()
        school = db.query(School).filter(School.id == a.school_id).first() if a.school_id else None
        rows.append({
            "professor_id": a.teacher_id,
            "professor": a.teacher.name if a.teacher else None,
            "tipo": tipo.name if tipo else None,
            "dia": _day_name(a.day_of_week), "slot": a.slot_number,
            "escola": school.name if school else None,
        })

    # Summarize per teacher
    from collections import defaultdict
    por_prof: dict = defaultdict(list)
    for r in rows:
        por_prof[r["professor"]].append(r)

    resumo = [
        {"professor": p, "total_slots": len(items), "servicos": items}
        for p, items in sorted(por_prof.items())
    ]
    return _j({"total_atribuicoes": len(rows), "por_professor": resumo})


def _tool_ver_regras(db: Session, cluster_id: int, academic_year_id: int = None) -> str:
    q = db.query(SchedulingRules).filter(SchedulingRules.cluster_id == cluster_id)
    if academic_year_id:
        q = q.filter(SchedulingRules.academic_year_id == academic_year_id)
    rules = q.all()
    if not rules:
        return _j({"aviso": "Sem regras configuradas — serão usados valores por omissão", "valores_padrao": {
            "max_aulas_dia_turma": 5, "max_aulas_dia_professor": 6,
            "max_aulas_consecutivas_turma": 2, "max_aulas_consecutivas_professor": 4,
            "sem_gaps_alunos": True, "minimizar_gaps_professor": True,
        }})
    result = []
    for r in rules:
        year = db.query(AcademicYear).filter(AcademicYear.id == r.academic_year_id).first() if r.academic_year_id else None
        result.append({
            "id": r.id,
            "ano_letivo": year.name if year else "global",
            "max_aulas_dia_turma": r.max_periods_per_day_class,
            "max_aulas_dia_professor": r.max_periods_per_day_teacher,
            "max_consecutivas_turma": r.max_consecutive_periods_class,
            "max_consecutivas_professor": r.max_consecutive_periods_teacher,
            "sem_gaps_alunos": r.no_student_gaps,
            "minimizar_gaps_professor": r.minimize_teacher_gaps,
            "sem_mesma_disciplina_2x_dia": r.no_same_subject_twice_per_day,
            "alunos_comecam_slot1": r.students_start_slot_1,
            "sem_ed_fisica_apos_almoco": r.no_pe_after_lunch,
            "almoco_apos_slot": r.lunch_after_slot,
        })
    return _j({"regras": result})


# ── Dispatcher ────────────────────────────────────────────────────────────────

def _execute_tool(name: str, inp: dict, db: Session) -> str:
    try:
        dispatch = {
            "obter_contexto":            lambda: _tool_obter_contexto(db),
            "listar_professores":        lambda: _tool_listar_professores(db, **inp),
            "atualizar_professor":       lambda: _tool_atualizar_professor(db, **inp),
            "listar_turmas":             lambda: _tool_listar_turmas(db, **inp),
            "ver_estado_horario":        lambda: _tool_ver_estado_horario(db, **inp),
            "ver_preflight_horario":     lambda: _tool_ver_preflight(db, **inp),
            "criar_horario":             lambda: _tool_criar_horario(db, **inp),
            "iniciar_geracao":           lambda: _tool_iniciar_geracao(db, **inp),
            "ver_horario_professor":     lambda: _tool_ver_horario_professor(db, **inp),
            "ver_horario_turma":         lambda: _tool_ver_horario_turma(db, **inp),
            "mover_aula":                lambda: _tool_mover_aula(db, **inp),
            "ver_distribuicao_servico":  lambda: _tool_ver_distribuicao(db, **inp),
            "definir_componentes_letivos": lambda: _tool_definir_componentes(db, **inp),
            "listar_servico_nao_letivo": lambda: _tool_listar_servico_nao_letivo(db, **inp),
            "ver_regras_horario":        lambda: _tool_ver_regras(db, **inp),
        }
        fn = dispatch.get(name)
        if fn is None:
            return _j({"erro": f"Ferramenta desconhecida: {name}"})
        return fn()
    except Exception as exc:
        return _j({"erro": str(exc)})


# ── OpenAI-format tool definitions (Gemini OpenAI-compatible endpoint) ────────

def _openai_tools() -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in _TOOLS
    ]


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "GEMINI_API_KEY não configurada. "
                "Obtém a tua chave gratuita em aistudio.google.com e adiciona ao ficheiro .env."
            ),
        )

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    # System message + conversation history
    messages: list = [{"role": "system", "content": _SYSTEM}]
    for m in request.messages:
        messages.append({"role": m.role, "content": m.content})

    tools = _openai_tools()
    tools_called: list = []

    for _ in range(10):
        response = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        choice = response.choices[0]
        msg = choice.message

        # No tool calls — final answer
        if not msg.tool_calls:
            return {"response": msg.content or "", "tools_called": tools_called}

        # Add assistant turn (with tool_calls) to history
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        # Execute each tool and add results
        for tc in msg.tool_calls:
            tools_called.append(tc.function.name)
            args = json.loads(tc.function.arguments)
            result = _execute_tool(tc.function.name, args, db)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return {"response": "Não foi possível processar o pedido.", "tools_called": tools_called}
