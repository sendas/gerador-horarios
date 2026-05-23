import os
import json
import threading
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    Cluster, School, AcademicYear, Timetable, Teacher, Class,
    ScheduledLesson, CurriculumEntry, NonTeachingAssignment, NonTeachingType,
    SchedulingRules, TimeSlotConfig, Subject, TeacherSchoolAssignment,
    Room, TeacherSubject, TeacherAvailability,
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
    # ── Disciplinas ───────────────────────────────────────────────────────────
    {
        "name": "listar_disciplinas",
        "description": (
            "Lista todas as disciplinas de um agrupamento com código, estrutura semanal, "
            "regime (anual/semestral) e quantas turmas a têm no currículo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "integer", "description": "ID do agrupamento"},
                "academic_year_id": {"type": "integer", "description": "Contar turmas neste ano letivo (opcional)"},
            },
            "required": ["cluster_id"],
        },
    },
    {
        "name": "renomear_disciplina",
        "description": (
            "Renomeia uma disciplina existente. Usa listar_disciplinas para obter o ID. "
            "Útil para corrigir capitalização ou inconsistências de nomes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "subject_id": {"type": "integer", "description": "ID da disciplina a renomear"},
                "novo_nome": {"type": "string", "description": "Novo nome da disciplina"},
                "novo_codigo": {"type": "string", "description": "Novo código (opcional)"},
            },
            "required": ["subject_id", "novo_nome"],
        },
    },
    {
        "name": "unificar_disciplinas",
        "description": (
            "Unifica duas disciplinas: migra todas as entradas curriculares, atribuições de professores "
            "e histórico da disciplina a remover para a disciplina a manter, depois elimina a duplicada. "
            "IRREVERSÍVEL — confirma sempre os IDs com listar_disciplinas antes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "subject_id_manter": {"type": "integer", "description": "ID da disciplina a manter (destino)"},
                "subject_id_remover": {"type": "integer", "description": "ID da disciplina a eliminar (origem)"},
            },
            "required": ["subject_id_manter", "subject_id_remover"],
        },
    },
    {
        "name": "ver_curriculo_turma",
        "description": (
            "Mostra o currículo completo de uma turma: disciplinas, horas/semana, "
            "professor atribuído e estrutura de aulas. Usa listar_turmas para obter o ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "class_id": {"type": "integer", "description": "ID da turma"},
            },
            "required": ["class_id"],
        },
    },
    # ── Salas ─────────────────────────────────────────────────────────────────
    {
        "name": "listar_salas",
        "description": "Lista salas disponíveis numa escola ou agrupamento com capacidade e tipo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "integer", "description": "ID do agrupamento"},
                "school_id": {"type": "integer", "description": "Filtrar por escola (opcional)"},
            },
            "required": ["cluster_id"],
        },
    },
    # ── Atribuição ────────────────────────────────────────────────────────────
    {
        "name": "ver_atribuicao_professores",
        "description": (
            "Mostra as atribuições de professores a turmas/disciplinas num ano letivo: "
            "quais professores dão quais disciplinas a que turmas e com quantas horas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo"},
                "teacher_id": {"type": "integer", "description": "Filtrar por professor (opcional)"},
                "subject_id": {"type": "integer", "description": "Filtrar por disciplina (opcional)"},
            },
            "required": ["academic_year_id"],
        },
    },
    {
        "name": "ver_disponibilidade_professor",
        "description": (
            "Mostra os slots de indisponibilidade de um professor num ano letivo "
            "(slots onde NÃO pode ter aulas). Útil para diagnosticar conflitos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "teacher_id": {"type": "integer", "description": "ID do professor"},
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo"},
            },
            "required": ["teacher_id", "academic_year_id"],
        },
    },
    # ── Anos letivos ──────────────────────────────────────────────────────────
    {
        "name": "listar_anos_letivos",
        "description": (
            "Lista todos os anos letivos de um agrupamento com estado ativo/inativo "
            "e número de turmas e horários."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "integer", "description": "ID do agrupamento"},
            },
            "required": ["cluster_id"],
        },
    },
    # ── Regras ────────────────────────────────────────────────────────────────
    {
        "name": "atribuir_professores_por_disciplina",
        "description": (
            "Atribui automaticamente professores às entradas curriculares sem professor, "
            "equilibrando a carga horária. Usa especialidades (TeacherSubject) se existirem; "
            "com usar_qualquer_professor=true atribui a qualquer professor do cluster quando "
            "não há especialista. Por defeito não sobrescreve atribuições já existentes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo"},
                "sobrescrever": {
                    "type": "boolean",
                    "description": "Se true, sobrescreve atribuições já existentes (padrão: false)",
                },
                "subject_id": {
                    "type": "integer",
                    "description": "Limitar a uma disciplina específica (opcional)",
                },
                "usar_qualquer_professor": {
                    "type": "boolean",
                    "description": "Se true, quando não há especialista usa qualquer professor do cluster (padrão: false)",
                },
            },
            "required": ["academic_year_id"],
        },
    },
    {
        "name": "verificar_duplicados_curriculo",
        "description": (
            "Verifica se há disciplinas duplicadas no currículo das turmas de um ano letivo — "
            "mesma disciplina atribuída mais de uma vez à mesma turma. "
            "Retorna lista de problemas encontrados e resumo por turma."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo a verificar"},
            },
            "required": ["academic_year_id"],
        },
    },
    # ── Criar / editar / eliminar Professores ─────────────────────────────────
    {
        "name": "criar_professor",
        "description": "Cria um novo professor num agrupamento.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "integer", "description": "ID do agrupamento"},
                "name": {"type": "string", "description": "Nome completo"},
                "email": {"type": "string", "description": "Email (opcional)"},
                "birth_date": {"type": "string", "description": "Data nascimento YYYY-MM-DD (opcional)"},
                "teaching_component": {"type": "integer", "description": "Componente letiva h/semana (opcional)"},
                "credit_hours": {"type": "integer", "description": "Horas de redução/crédito (opcional)"},
                "max_daily_lessons": {"type": "integer", "description": "Máximo aulas/dia (padrão 5)"},
            },
            "required": ["cluster_id", "name"],
        },
    },
    {
        "name": "eliminar_professor",
        "description": (
            "Elimina um professor. Falha se tiver aulas marcadas num horário gerado. "
            "Usa listar_professores para obter o ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "teacher_id": {"type": "integer", "description": "ID do professor"},
                "forcar": {"type": "boolean", "description": "Se true, remove mesmo com entradas curriculares (padrão: false)"},
            },
            "required": ["teacher_id"],
        },
    },
    {
        "name": "definir_especialidade_professor",
        "description": (
            "Adiciona ou remove uma especialidade (disciplina) a um professor. "
            "Usa listar_professores e listar_disciplinas para obter IDs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "teacher_id": {"type": "integer", "description": "ID do professor"},
                "subject_id": {"type": "integer", "description": "ID da disciplina"},
                "acao": {"type": "string", "description": "'adicionar' ou 'remover'"},
            },
            "required": ["teacher_id", "subject_id", "acao"],
        },
    },
    # ── Criar / editar / eliminar Turmas ──────────────────────────────────────
    {
        "name": "criar_turma",
        "description": "Cria uma nova turma num ano letivo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo"},
                "school_id": {"type": "integer", "description": "ID da escola"},
                "name": {"type": "string", "description": "Nome da turma (ex: '8A')"},
                "year_level": {"type": "integer", "description": "Ano de escolaridade (ex: 8)"},
                "num_students": {"type": "integer", "description": "Número de alunos (padrão 25)"},
            },
            "required": ["academic_year_id", "school_id", "name", "year_level"],
        },
    },
    {
        "name": "atualizar_turma",
        "description": "Atualiza dados de uma turma: nome, ano de escolaridade, número de alunos ou notas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "class_id": {"type": "integer", "description": "ID da turma"},
                "name": {"type": "string", "description": "Novo nome (opcional)"},
                "year_level": {"type": "integer", "description": "Novo ano de escolaridade (opcional)"},
                "num_students": {"type": "integer", "description": "Novo número de alunos (opcional)"},
                "notes": {"type": "string", "description": "Notas/observações (opcional)"},
            },
            "required": ["class_id"],
        },
    },
    {
        "name": "eliminar_turma",
        "description": "Elimina uma turma e o seu currículo. IRREVERSÍVEL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "class_id": {"type": "integer", "description": "ID da turma"},
            },
            "required": ["class_id"],
        },
    },
    # ── Criar / eliminar Disciplinas ──────────────────────────────────────────
    {
        "name": "criar_disciplina",
        "description": "Cria uma nova disciplina num agrupamento.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "integer", "description": "ID do agrupamento"},
                "name": {"type": "string", "description": "Nome da disciplina"},
                "code": {"type": "string", "description": "Código (opcional)"},
                "weekly_structure": {"type": "string", "description": "Estrutura semanal: '1', '1+1', '2', '2+1', '1+1+1' (padrão: '1+1')"},
                "regime": {"type": "string", "description": "'annual' ou 'semestral' (padrão: 'annual')"},
                "is_physical_education": {"type": "boolean", "description": "É Educação Física? (padrão: false)"},
            },
            "required": ["cluster_id", "name"],
        },
    },
    {
        "name": "eliminar_disciplina",
        "description": "Elimina uma disciplina se não tiver entradas curriculares. IRREVERSÍVEL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject_id": {"type": "integer", "description": "ID da disciplina"},
            },
            "required": ["subject_id"],
        },
    },
    # ── Gestão de Currículo ───────────────────────────────────────────────────
    {
        "name": "adicionar_entrada_curriculo",
        "description": (
            "Adiciona uma disciplina ao currículo de uma turma com horas/semana e estrutura de blocos. "
            "Usa listar_turmas e listar_disciplinas para obter IDs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "class_id": {"type": "integer", "description": "ID da turma"},
                "subject_id": {"type": "integer", "description": "ID da disciplina"},
                "hours_per_week": {"type": "number", "description": "Horas por semana (ex: 2.0)"},
                "split_count": {"type": "integer", "description": "Número de blocos/aulas por semana (padrão: igual a hours_per_week)"},
                "consecutive_pairs": {"type": "integer", "description": "Número de blocos que devem ser duplos consecutivos (padrão: 0)"},
                "teacher_id": {"type": "integer", "description": "Professor a atribuir (opcional)"},
                "is_semestral": {"type": "boolean", "description": "Disciplina semestral? (padrão: false)"},
                "semester": {"type": "integer", "description": "Semestre: 1 ou 2 (se semestral)"},
            },
            "required": ["class_id", "subject_id", "hours_per_week"],
        },
    },
    {
        "name": "atualizar_entrada_curriculo",
        "description": "Atualiza horas, professor, blocos ou regime semestral de uma entrada curricular.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "integer", "description": "ID da entrada curricular"},
                "hours_per_week": {"type": "number", "description": "Novas horas/semana (opcional)"},
                "split_count": {"type": "integer", "description": "Novo número de blocos (opcional)"},
                "consecutive_pairs": {"type": "integer", "description": "Novos blocos duplos consecutivos (opcional)"},
                "teacher_id": {"type": "integer", "description": "Novo professor (null para remover)"},
                "is_semestral": {"type": "boolean", "description": "Alterar para semestral/anual (opcional)"},
                "semester": {"type": "integer", "description": "Novo semestre: 1 ou 2 (opcional)"},
            },
            "required": ["entry_id"],
        },
    },
    {
        "name": "remover_entrada_curriculo",
        "description": "Remove uma disciplina do currículo de uma turma. IRREVERSÍVEL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "integer", "description": "ID da entrada curricular"},
            },
            "required": ["entry_id"],
        },
    },
    # ── Disponibilidade de professor ──────────────────────────────────────────
    {
        "name": "definir_disponibilidade_professor",
        "description": (
            "Define os slots de indisponibilidade de um professor num ano letivo. "
            "Passa a lista de slots onde o professor NÃO pode ter aulas. "
            "Dias: 0=Segunda, 1=Terça, 2=Quarta, 3=Quinta, 4=Sexta. "
            "Substitui completamente a disponibilidade anterior se substituir=true."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "teacher_id": {"type": "integer", "description": "ID do professor"},
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo"},
                "slots_indisponiveis": {
                    "type": "array",
                    "description": "Lista de slots indisponíveis: [{dia: 0-4, slot: 1-N}]",
                    "items": {"type": "object", "properties": {"dia": {"type": "integer"}, "slot": {"type": "integer"}}},
                },
                "substituir": {"type": "boolean", "description": "Se true, apaga indisponibilidades anteriores (padrão: true)"},
            },
            "required": ["teacher_id", "academic_year_id", "slots_indisponiveis"],
        },
    },
    # ── Regras de horário ─────────────────────────────────────────────────────
    {
        "name": "atualizar_regras_horario",
        "description": (
            "Cria ou atualiza regras de horário para um agrupamento/ano letivo. "
            "Qualquer campo omitido mantém o valor atual."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "integer", "description": "ID do agrupamento"},
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo (null = global)"},
                "max_aulas_dia_turma": {"type": "integer", "description": "Máximo aulas/dia por turma"},
                "max_aulas_dia_professor": {"type": "integer", "description": "Máximo aulas/dia por professor"},
                "max_consecutivas_turma": {"type": "integer", "description": "Máximo aulas consecutivas por turma"},
                "max_consecutivas_professor": {"type": "integer", "description": "Máximo aulas consecutivas por professor"},
                "sem_gaps_alunos": {"type": "boolean", "description": "Proibir intervalos entre aulas das turmas"},
                "sem_mesma_disciplina_2x_dia": {"type": "boolean", "description": "Proibir mesma disciplina 2x no mesmo dia"},
                "alunos_comecam_slot1": {"type": "boolean", "description": "Turmas começam sempre no slot 1"},
                "sem_ed_fisica_apos_almoco": {"type": "boolean", "description": "Proibir Ed. Física após almoço"},
                "almoco_apos_slot": {"type": "integer", "description": "Último slot antes do almoço"},
            },
            "required": ["cluster_id"],
        },
    },
    # ── Gestão de horários ────────────────────────────────────────────────────
    {
        "name": "eliminar_horario",
        "description": "Elimina um horário e todas as aulas geradas. IRREVERSÍVEL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timetable_id": {"type": "integer", "description": "ID do horário"},
            },
            "required": ["timetable_id"],
        },
    },
    {
        "name": "limpar_aulas_horario",
        "description": "Apaga todas as aulas geradas de um horário, repondo-o para estado de rascunho.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timetable_id": {"type": "integer", "description": "ID do horário"},
            },
            "required": ["timetable_id"],
        },
    },
    # ── Serviço não letivo ────────────────────────────────────────────────────
    {
        "name": "listar_tipos_servico",
        "description": "Lista os tipos de serviço não letivo disponíveis (ex: Direção de Turma, Apoio, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "adicionar_servico_nao_letivo",
        "description": (
            "Atribui um slot de serviço não letivo a um professor. "
            "Usa listar_tipos_servico para obter o tipo_id. "
            "Dias: 0=Segunda … 4=Sexta."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "teacher_id": {"type": "integer", "description": "ID do professor"},
                "academic_year_id": {"type": "integer", "description": "ID do ano letivo"},
                "tipo_id": {"type": "integer", "description": "ID do tipo de serviço"},
                "dia": {"type": "integer", "description": "Dia: 0=Seg, 1=Ter, 2=Qua, 3=Qui, 4=Sex"},
                "slot": {"type": "integer", "description": "Número do slot/tempo"},
                "school_id": {"type": "integer", "description": "ID da escola (opcional)"},
            },
            "required": ["teacher_id", "academic_year_id", "tipo_id", "dia", "slot"],
        },
    },
    {
        "name": "remover_servico_nao_letivo",
        "description": "Remove um registo de serviço não letivo. Usa listar_servico_nao_letivo para obter o ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "assignment_id": {"type": "integer", "description": "ID do registo de serviço não letivo"},
            },
            "required": ["assignment_id"],
        },
    },
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


def _tool_renomear_disciplina(db: Session, subject_id: int, novo_nome: str, novo_codigo: str = None) -> str:
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        return _j({"erro": f"Disciplina {subject_id} não encontrada"})
    nome_antigo = subj.name
    subj.name = novo_nome.strip()
    if novo_codigo is not None:
        subj.code = novo_codigo.strip() or None
    db.commit()
    return _j({"ok": True, "nome_anterior": nome_antigo, "nome_novo": subj.name, "id": subject_id})


def _tool_unificar_disciplinas(db: Session, subject_id_manter: int, subject_id_remover: int) -> str:
    manter = db.query(Subject).filter(Subject.id == subject_id_manter).first()
    remover = db.query(Subject).filter(Subject.id == subject_id_remover).first()
    if not manter:
        return _j({"erro": f"Disciplina a manter ({subject_id_manter}) não encontrada"})
    if not remover:
        return _j({"erro": f"Disciplina a remover ({subject_id_remover}) não encontrada"})
    if subject_id_manter == subject_id_remover:
        return _j({"erro": "Os dois IDs são iguais"})

    # Migrate curriculum entries
    entries_migradas = (
        db.query(CurriculumEntry)
        .filter(CurriculumEntry.subject_id == subject_id_remover)
        .all()
    )
    for e in entries_migradas:
        e.subject_id = subject_id_manter

    # Migrate teacher-subject assignments (skip if already exists)
    for ts in db.query(TeacherSubject).filter(TeacherSubject.subject_id == subject_id_remover).all():
        exists = db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == ts.teacher_id,
            TeacherSubject.subject_id == subject_id_manter,
        ).first()
        if exists:
            db.delete(ts)
        else:
            ts.subject_id = subject_id_manter

    db.flush()
    nome_removida = remover.name
    db.delete(remover)
    db.commit()
    return _j({
        "ok": True,
        "disciplina_mantida": {"id": subject_id_manter, "nome": manter.name},
        "disciplina_removida": nome_removida,
        "entradas_curriculares_migradas": len(entries_migradas),
    })


def _tool_criar_professor(
    db: Session, cluster_id: int, name: str, email: str = None,
    birth_date: str = None, teaching_component: int = None,
    credit_hours: int = None, max_daily_lessons: int = 5,
) -> str:
    from datetime import date as date_type
    bd = None
    if birth_date:
        try:
            bd = date_type.fromisoformat(birth_date)
        except ValueError:
            return _j({"erro": "birth_date inválido, usar YYYY-MM-DD"})
    t = Teacher(
        cluster_id=cluster_id, name=name.strip(), email=email or None,
        birth_date=bd, teaching_component=teaching_component,
        credit_hours=credit_hours or 0, max_daily_lessons=max_daily_lessons,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _j({"ok": True, "id": t.id, "nome": t.name})


def _tool_eliminar_professor(db: Session, teacher_id: int, forcar: bool = False) -> str:
    t = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not t:
        return _j({"erro": f"Professor {teacher_id} não encontrado"})
    lessons = db.query(ScheduledLesson).filter(ScheduledLesson.teacher_id == teacher_id).count()
    if lessons and not forcar:
        return _j({"erro": f"Professor tem {lessons} aulas marcadas. Usa forcar=true para eliminar mesmo assim."})
    nome = t.name
    db.delete(t)
    db.commit()
    return _j({"ok": True, "eliminado": nome})


def _tool_definir_especialidade_professor(
    db: Session, teacher_id: int, subject_id: int, acao: str
) -> str:
    acao = acao.lower().strip()
    if acao not in ("adicionar", "remover"):
        return _j({"erro": "acao deve ser 'adicionar' ou 'remover'"})
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not teacher or not subj:
        return _j({"erro": "Professor ou disciplina não encontrados"})
    existing = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == teacher_id, TeacherSubject.subject_id == subject_id
    ).first()
    if acao == "adicionar":
        if existing:
            return _j({"ok": True, "nota": "Especialidade já existia", "professor": teacher.name, "disciplina": subj.name})
        db.add(TeacherSubject(teacher_id=teacher_id, subject_id=subject_id))
        db.commit()
        return _j({"ok": True, "professor": teacher.name, "disciplina": subj.name, "acao": "adicionada"})
    else:
        if not existing:
            return _j({"ok": True, "nota": "Especialidade não existia", "professor": teacher.name, "disciplina": subj.name})
        db.delete(existing)
        db.commit()
        return _j({"ok": True, "professor": teacher.name, "disciplina": subj.name, "acao": "removida"})


def _tool_criar_turma(
    db: Session, academic_year_id: int, school_id: int, name: str,
    year_level: int, num_students: int = 25,
) -> str:
    c = Class(
        academic_year_id=academic_year_id, school_id=school_id,
        name=name.strip(), year_level=year_level, num_students=num_students,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _j({"ok": True, "id": c.id, "nome": c.name, "ano": c.year_level})


def _tool_atualizar_turma(
    db: Session, class_id: int, name: str = None, year_level: int = None,
    num_students: int = None, notes: str = None,
) -> str:
    c = db.query(Class).filter(Class.id == class_id).first()
    if not c:
        return _j({"erro": f"Turma {class_id} não encontrada"})
    if name is not None: c.name = name.strip()
    if year_level is not None: c.year_level = year_level
    if num_students is not None: c.num_students = num_students
    if notes is not None: c.notes = notes
    db.commit()
    return _j({"ok": True, "id": c.id, "nome": c.name})


def _tool_eliminar_turma(db: Session, class_id: int) -> str:
    c = db.query(Class).filter(Class.id == class_id).first()
    if not c:
        return _j({"erro": f"Turma {class_id} não encontrada"})
    nome = c.name
    db.delete(c)
    db.commit()
    return _j({"ok": True, "eliminada": nome})


def _tool_criar_disciplina(
    db: Session, cluster_id: int, name: str, code: str = None,
    weekly_structure: str = "1+1", regime: str = "annual",
    is_physical_education: bool = False,
) -> str:
    s = Subject(
        cluster_id=cluster_id, name=name.strip(), code=code or None,
        weekly_structure=weekly_structure, regime=regime,
        is_physical_education=is_physical_education,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _j({"ok": True, "id": s.id, "nome": s.name})


def _tool_eliminar_disciplina(db: Session, subject_id: int) -> str:
    s = db.query(Subject).filter(Subject.id == subject_id).first()
    if not s:
        return _j({"erro": f"Disciplina {subject_id} não encontrada"})
    count = db.query(CurriculumEntry).filter(CurriculumEntry.subject_id == subject_id).count()
    if count:
        return _j({"erro": f"Disciplina tem {count} entradas curriculares. Remove-as primeiro ou usa unificar_disciplinas."})
    nome = s.name
    db.delete(s)
    db.commit()
    return _j({"ok": True, "eliminada": nome})


def _tool_adicionar_entrada_curriculo(
    db: Session, class_id: int, subject_id: int, hours_per_week: float,
    split_count: int = None, consecutive_pairs: int = 0,
    teacher_id: int = None, is_semestral: bool = False, semester: int = None,
) -> str:
    if split_count is None:
        split_count = max(1, int(hours_per_week))
    e = CurriculumEntry(
        class_id=class_id, subject_id=subject_id, hours_per_week=hours_per_week,
        split_count=split_count, consecutive_pairs=consecutive_pairs,
        teacher_id=teacher_id, is_semestral=is_semestral, semester=semester,
        is_split=split_count > 1,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    cls = db.query(Class).filter(Class.id == class_id).first()
    return _j({"ok": True, "id": e.id, "turma": cls.name if cls else class_id,
               "disciplina": subj.name if subj else subject_id, "horas": hours_per_week})


def _tool_atualizar_entrada_curriculo(
    db: Session, entry_id: int, hours_per_week: float = None,
    split_count: int = None, consecutive_pairs: int = None,
    teacher_id: int = None, is_semestral: bool = None, semester: int = None,
) -> str:
    e = db.query(CurriculumEntry).filter(CurriculumEntry.id == entry_id).first()
    if not e:
        return _j({"erro": f"Entrada curricular {entry_id} não encontrada"})
    if hours_per_week is not None: e.hours_per_week = hours_per_week
    if split_count is not None:
        e.split_count = split_count
        e.is_split = split_count > 1
    if consecutive_pairs is not None: e.consecutive_pairs = consecutive_pairs
    if teacher_id is not None: e.teacher_id = teacher_id if teacher_id > 0 else None
    if is_semestral is not None: e.is_semestral = is_semestral
    if semester is not None: e.semester = semester
    db.commit()
    return _j({"ok": True, "id": entry_id})


def _tool_remover_entrada_curriculo(db: Session, entry_id: int) -> str:
    e = db.query(CurriculumEntry).filter(CurriculumEntry.id == entry_id).first()
    if not e:
        return _j({"erro": f"Entrada curricular {entry_id} não encontrada"})
    db.delete(e)
    db.commit()
    return _j({"ok": True, "removida": entry_id})


def _tool_definir_disponibilidade_professor(
    db: Session, teacher_id: int, academic_year_id: int,
    slots_indisponiveis: list, substituir: bool = True,
) -> str:
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        return _j({"erro": f"Professor {teacher_id} não encontrado"})
    if substituir:
        db.query(TeacherAvailability).filter(
            TeacherAvailability.teacher_id == teacher_id,
            TeacherAvailability.academic_year_id == academic_year_id,
            TeacherAvailability.is_available.is_(False),
        ).delete()
    added = 0
    for s in slots_indisponiveis:
        dia = int(s.get("dia", -1))
        slot = int(s.get("slot", -1))
        if dia < 0 or slot < 1:
            continue
        exists = db.query(TeacherAvailability).filter(
            TeacherAvailability.teacher_id == teacher_id,
            TeacherAvailability.academic_year_id == academic_year_id,
            TeacherAvailability.day_of_week == dia,
            TeacherAvailability.slot_number == slot,
        ).first()
        if not exists:
            db.add(TeacherAvailability(
                teacher_id=teacher_id, academic_year_id=academic_year_id,
                day_of_week=dia, slot_number=slot, is_available=False,
            ))
            added += 1
    db.commit()
    return _j({"ok": True, "professor": teacher.name, "slots_indisponiveis_definidos": added})


def _tool_atualizar_regras_horario(
    db: Session, cluster_id: int, academic_year_id: int = None,
    max_aulas_dia_turma: int = None, max_aulas_dia_professor: int = None,
    max_consecutivas_turma: int = None, max_consecutivas_professor: int = None,
    sem_gaps_alunos: bool = None, sem_mesma_disciplina_2x_dia: bool = None,
    alunos_comecam_slot1: bool = None, sem_ed_fisica_apos_almoco: bool = None,
    almoco_apos_slot: int = None,
) -> str:
    q = db.query(SchedulingRules).filter(SchedulingRules.cluster_id == cluster_id)
    if academic_year_id:
        q = q.filter(SchedulingRules.academic_year_id == academic_year_id)
    else:
        q = q.filter(SchedulingRules.academic_year_id.is_(None))
    r = q.first()
    if not r:
        r = SchedulingRules(cluster_id=cluster_id, academic_year_id=academic_year_id)
        db.add(r)
    if max_aulas_dia_turma is not None: r.max_periods_per_day_class = max_aulas_dia_turma
    if max_aulas_dia_professor is not None: r.max_periods_per_day_teacher = max_aulas_dia_professor
    if max_consecutivas_turma is not None: r.max_consecutive_periods_class = max_consecutivas_turma
    if max_consecutivas_professor is not None: r.max_consecutive_periods_teacher = max_consecutivas_professor
    if sem_gaps_alunos is not None: r.no_student_gaps = sem_gaps_alunos
    if sem_mesma_disciplina_2x_dia is not None: r.no_same_subject_twice_per_day = sem_mesma_disciplina_2x_dia
    if alunos_comecam_slot1 is not None: r.students_start_slot_1 = alunos_comecam_slot1
    if sem_ed_fisica_apos_almoco is not None: r.no_pe_after_lunch = sem_ed_fisica_apos_almoco
    if almoco_apos_slot is not None: r.lunch_after_slot = almoco_apos_slot
    db.commit()
    return _j({"ok": True, "cluster_id": cluster_id, "academic_year_id": academic_year_id})


def _tool_eliminar_horario(db: Session, timetable_id: int) -> str:
    t = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not t:
        return _j({"erro": f"Horário {timetable_id} não encontrado"})
    nome = t.name
    db.delete(t)
    db.commit()
    return _j({"ok": True, "eliminado": nome})


def _tool_limpar_aulas_horario(db: Session, timetable_id: int) -> str:
    t = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not t:
        return _j({"erro": f"Horário {timetable_id} não encontrado"})
    deleted = db.query(ScheduledLesson).filter(ScheduledLesson.timetable_id == timetable_id).delete()
    t.status = "draft"
    t.solver_status = None
    t.generation_log = None
    db.commit()
    return _j({"ok": True, "aulas_removidas": deleted, "status": "draft"})


def _tool_listar_tipos_servico(db: Session) -> str:
    tipos = db.query(NonTeachingType).all()
    return _j({"tipos": [{"id": tp.id, "nome": tp.name} for tp in tipos]})


def _tool_adicionar_servico_nao_letivo(
    db: Session, teacher_id: int, academic_year_id: int,
    tipo_id: int, dia: int, slot: int, school_id: int = None,
) -> str:
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        return _j({"erro": f"Professor {teacher_id} não encontrado"})
    a = NonTeachingAssignment(
        teacher_id=teacher_id, academic_year_id=academic_year_id,
        non_teaching_type_id=tipo_id, day_of_week=dia,
        slot_number=slot, school_id=school_id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _j({"ok": True, "id": a.id, "professor": teacher.name, "dia": _day_name(dia), "slot": slot})


def _tool_remover_servico_nao_letivo(db: Session, assignment_id: int) -> str:
    a = db.query(NonTeachingAssignment).filter(NonTeachingAssignment.id == assignment_id).first()
    if not a:
        return _j({"erro": f"Registo {assignment_id} não encontrado"})
    db.delete(a)
    db.commit()
    return _j({"ok": True, "removido": assignment_id})


def _tool_listar_disciplinas(db: Session, cluster_id: int, academic_year_id: int = None) -> str:
    subjects = db.query(Subject).filter(Subject.cluster_id == cluster_id).order_by(Subject.name).all()
    rows = []
    for s in subjects:
        count = 0
        if academic_year_id:
            count = (
                db.query(CurriculumEntry)
                .join(CurriculumEntry.class_)
                .filter(Class.academic_year_id == academic_year_id, CurriculumEntry.subject_id == s.id)
                .count()
            )
        rows.append({
            "id": s.id, "nome": s.name, "codigo": s.code,
            "estrutura_semanal": s.weekly_structure, "regime": s.regime,
            "educacao_fisica": s.is_physical_education,
            "turmas_com_esta_disciplina": count if academic_year_id else "n/a",
        })
    return _j({"total": len(rows), "disciplinas": rows})


def _tool_ver_curriculo_turma(db: Session, class_id: int) -> str:
    class_ = db.query(Class).filter(Class.id == class_id).first()
    if not class_:
        return _j({"erro": f"Turma {class_id} não encontrada"})
    entries = db.query(CurriculumEntry).filter(CurriculumEntry.class_id == class_id).all()
    rows = []
    total_hours = 0.0
    for e in entries:
        subj = db.query(Subject).filter(Subject.id == e.subject_id).first()
        teacher = db.query(Teacher).filter(Teacher.id == e.teacher_id).first() if e.teacher_id else None
        rows.append({
            "id": e.id,
            "disciplina": subj.name if subj else "?",
            "codigo": subj.code if subj else None,
            "horas_semana": e.hours_per_week,
            "blocos": e.split_count,
            "pares_consecutivos": e.consecutive_pairs,
            "semestral": e.is_semestral,
            "semestre": e.semester,
            "professor": teacher.name if teacher else "Não atribuído",
        })
        total_hours += e.hours_per_week
    return _j({
        "turma": class_.name,
        "ano_escolaridade": class_.year_level,
        "total_horas_semana": total_hours,
        "total_entradas": len(rows),
        "curriculo": rows,
    })


def _tool_atribuir_professores_por_disciplina(
    db: Session, academic_year_id: int, sobrescrever: bool = False,
    subject_id: int = None, usar_qualquer_professor: bool = False,
) -> str:
    # Get the cluster for fallback
    year = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    cluster_id = year.cluster_id if year else None

    q = (
        db.query(CurriculumEntry)
        .join(CurriculumEntry.class_)
        .filter(Class.academic_year_id == academic_year_id)
    )
    if subject_id:
        q = q.filter(CurriculumEntry.subject_id == subject_id)
    if not sobrescrever:
        q = q.filter(CurriculumEntry.teacher_id.is_(None))
    entries = q.all()

    # Build load map: teacher_id → total hours already assigned this year
    load: dict = {}
    for e in (
        db.query(CurriculumEntry)
        .join(CurriculumEntry.class_)
        .filter(Class.academic_year_id == academic_year_id, CurriculumEntry.teacher_id.isnot(None))
        .all()
    ):
        load[e.teacher_id] = load.get(e.teacher_id, 0) + e.hours_per_week

    # Cache teachers by subject specialty
    specialty_cache: dict = {}

    def get_candidates(sid: int):
        if sid not in specialty_cache:
            rows = db.query(TeacherSubject).filter(TeacherSubject.subject_id == sid).all()
            specialty_cache[sid] = [r.teacher_id for r in rows]
        return specialty_cache[sid]

    # All teachers in cluster for fallback
    all_teacher_ids = [
        t.id for t in db.query(Teacher).filter(Teacher.cluster_id == cluster_id).all()
    ] if cluster_id else []

    atribuidas = []
    sem_professor = []
    por_especialidade = 0
    por_fallback = 0

    for entry in entries:
        candidates = get_candidates(entry.subject_id)
        via_fallback = False

        if not candidates:
            if not usar_qualquer_professor or not all_teacher_ids:
                subj = db.query(Subject).filter(Subject.id == entry.subject_id).first()
                cls = db.query(Class).filter(Class.id == entry.class_id).first()
                sem_professor.append({
                    "turma": cls.name if cls else entry.class_id,
                    "disciplina": subj.name if subj else entry.subject_id,
                })
                continue
            candidates = all_teacher_ids
            via_fallback = True

        best_tid = min(candidates, key=lambda tid: load.get(tid, 0))
        teacher = db.query(Teacher).filter(Teacher.id == best_tid).first()
        subj = db.query(Subject).filter(Subject.id == entry.subject_id).first()
        cls = db.query(Class).filter(Class.id == entry.class_id).first()

        entry.teacher_id = best_tid
        load[best_tid] = load.get(best_tid, 0) + entry.hours_per_week

        if via_fallback:
            por_fallback += 1
        else:
            por_especialidade += 1

        atribuidas.append({
            "turma": cls.name if cls else entry.class_id,
            "disciplina": subj.name if subj else entry.subject_id,
            "professor": teacher.name if teacher else best_tid,
            "horas": entry.hours_per_week,
            "via": "fallback" if via_fallback else "especialidade",
        })

    db.commit()
    return _j({
        "atribuidas": len(atribuidas),
        "por_especialidade": por_especialidade,
        "por_fallback_sem_especialidade": por_fallback,
        "sem_professor_disponivel": len(sem_professor),
        "detalhes_atribuidas": atribuidas,
        "detalhes_sem_professor": sem_professor,
    })


def _tool_listar_salas(db: Session, cluster_id: int, school_id: int = None) -> str:
    schools = db.query(School).filter(School.cluster_id == cluster_id).all()
    school_ids = [s.id for s in schools]
    q = db.query(Room).filter(Room.school_id.in_(school_ids))
    if school_id:
        q = q.filter(Room.school_id == school_id)
    rooms = q.order_by(Room.name).all()
    school_map = {s.id: s.name for s in schools}
    rows = [
        {"id": r.id, "nome": r.name, "escola": school_map.get(r.school_id, "?"),
         "capacidade": r.capacity, "tipo": r.room_type}
        for r in rooms
    ]
    return _j({"total": len(rows), "salas": rows})


def _tool_ver_atribuicao_professores(
    db: Session, academic_year_id: int, teacher_id: int = None, subject_id: int = None
) -> str:
    q = (
        db.query(CurriculumEntry)
        .join(CurriculumEntry.class_)
        .filter(Class.academic_year_id == academic_year_id)
        .filter(CurriculumEntry.teacher_id.isnot(None))
    )
    if teacher_id:
        q = q.filter(CurriculumEntry.teacher_id == teacher_id)
    if subject_id:
        q = q.filter(CurriculumEntry.subject_id == subject_id)
    entries = q.all()
    rows = []
    for e in entries:
        teacher = db.query(Teacher).filter(Teacher.id == e.teacher_id).first()
        subj = db.query(Subject).filter(Subject.id == e.subject_id).first()
        class_ = db.query(Class).filter(Class.id == e.class_id).first()
        rows.append({
            "professor_id": e.teacher_id,
            "professor": teacher.name if teacher else "?",
            "disciplina_id": e.subject_id,
            "disciplina": subj.name if subj else "?",
            "turma_id": e.class_id,
            "turma": class_.name if class_ else "?",
            "horas_semana": e.hours_per_week,
        })
    sem_atribuicao = (
        db.query(CurriculumEntry)
        .join(CurriculumEntry.class_)
        .filter(Class.academic_year_id == academic_year_id, CurriculumEntry.teacher_id.is_(None))
        .count()
    )
    return _j({
        "total_atribuicoes": len(rows),
        "entradas_sem_professor": sem_atribuicao,
        "atribuicoes": rows,
    })


def _tool_ver_disponibilidade_professor(db: Session, teacher_id: int, academic_year_id: int) -> str:
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        return _j({"erro": f"Professor {teacher_id} não encontrado"})
    unavailable = (
        db.query(TeacherAvailability)
        .filter(
            TeacherAvailability.teacher_id == teacher_id,
            TeacherAvailability.academic_year_id == academic_year_id,
            TeacherAvailability.is_available.is_(False),
        )
        .order_by(TeacherAvailability.day_of_week, TeacherAvailability.slot_number)
        .all()
    )
    slots = [
        {"dia": _day_name(a.day_of_week), "slot": a.slot_number}
        for a in unavailable
    ]
    return _j({
        "professor": teacher.name,
        "total_indisponibilidades": len(slots),
        "slots_indisponiveis": slots,
        "nota": "Slots não listados são disponíveis",
    })


def _tool_verificar_duplicados_curriculo(db: Session, academic_year_id: int) -> str:
    classes = db.query(Class).filter(Class.academic_year_id == academic_year_id).all()
    problemas = []
    resumo = []
    for cls in classes:
        entries = db.query(CurriculumEntry).filter(CurriculumEntry.class_id == cls.id).all()
        contagem: dict = {}
        for e in entries:
            contagem.setdefault(e.subject_id, []).append(e.id)
        dups = {sid: ids for sid, ids in contagem.items() if len(ids) > 1}
        turma_ok = len(dups) == 0
        resumo.append({"turma": cls.name, "ok": turma_ok, "duplicados": len(dups)})
        for sid, ids in dups.items():
            subj = db.query(Subject).filter(Subject.id == sid).first()
            problemas.append({
                "turma": cls.name,
                "turma_id": cls.id,
                "disciplina": subj.name if subj else f"id={sid}",
                "disciplina_id": sid,
                "entradas_duplicadas": len(ids),
                "entry_ids": ids,
            })
    return _j({
        "total_turmas": len(classes),
        "turmas_com_duplicados": len([r for r in resumo if not r["ok"]]),
        "total_problemas": len(problemas),
        "problemas": problemas,
        "resumo_por_turma": resumo,
    })


def _tool_listar_anos_letivos(db: Session, cluster_id: int) -> str:
    years = (
        db.query(AcademicYear)
        .filter(AcademicYear.cluster_id == cluster_id)
        .order_by(AcademicYear.name.desc())
        .all()
    )
    rows = []
    for y in years:
        num_classes = db.query(Class).filter(Class.academic_year_id == y.id).count()
        num_timetables = db.query(Timetable).filter(Timetable.academic_year_id == y.id).count()
        rows.append({
            "id": y.id, "nome": y.name, "ativo": y.is_active,
            "num_turmas": num_classes, "num_horarios": num_timetables,
        })
    return _j({"anos_letivos": rows})


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
            "listar_disciplinas":        lambda: _tool_listar_disciplinas(db, **inp),
            "renomear_disciplina":       lambda: _tool_renomear_disciplina(db, **inp),
            "unificar_disciplinas":      lambda: _tool_unificar_disciplinas(db, **inp),
            "ver_curriculo_turma":       lambda: _tool_ver_curriculo_turma(db, **inp),
            "listar_salas":              lambda: _tool_listar_salas(db, **inp),
            "ver_atribuicao_professores": lambda: _tool_ver_atribuicao_professores(db, **inp),
            "ver_disponibilidade_professor": lambda: _tool_ver_disponibilidade_professor(db, **inp),
            "listar_anos_letivos":       lambda: _tool_listar_anos_letivos(db, **inp),
            "verificar_duplicados_curriculo": lambda: _tool_verificar_duplicados_curriculo(db, **inp),
            "atribuir_professores_por_disciplina": lambda: _tool_atribuir_professores_por_disciplina(db, **inp),
            "criar_professor":           lambda: _tool_criar_professor(db, **inp),
            "eliminar_professor":        lambda: _tool_eliminar_professor(db, **inp),
            "definir_especialidade_professor": lambda: _tool_definir_especialidade_professor(db, **inp),
            "criar_turma":               lambda: _tool_criar_turma(db, **inp),
            "atualizar_turma":           lambda: _tool_atualizar_turma(db, **inp),
            "eliminar_turma":            lambda: _tool_eliminar_turma(db, **inp),
            "criar_disciplina":          lambda: _tool_criar_disciplina(db, **inp),
            "eliminar_disciplina":       lambda: _tool_eliminar_disciplina(db, **inp),
            "adicionar_entrada_curriculo": lambda: _tool_adicionar_entrada_curriculo(db, **inp),
            "atualizar_entrada_curriculo": lambda: _tool_atualizar_entrada_curriculo(db, **inp),
            "remover_entrada_curriculo": lambda: _tool_remover_entrada_curriculo(db, **inp),
            "definir_disponibilidade_professor": lambda: _tool_definir_disponibilidade_professor(db, **inp),
            "atualizar_regras_horario":  lambda: _tool_atualizar_regras_horario(db, **inp),
            "eliminar_horario":          lambda: _tool_eliminar_horario(db, **inp),
            "limpar_aulas_horario":      lambda: _tool_limpar_aulas_horario(db, **inp),
            "listar_tipos_servico":      lambda: _tool_listar_tipos_servico(db),
            "adicionar_servico_nao_letivo": lambda: _tool_adicionar_servico_nao_letivo(db, **inp),
            "remover_servico_nao_letivo": lambda: _tool_remover_servico_nao_letivo(db, **inp),
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

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

# ── Streaming endpoint ────────────────────────────────────────────────────────

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

    def generate():
        from openai import OpenAI, RateLimitError, APIStatusError

        client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            timeout=25.0,
        )

        messages: list = [{"role": "system", "content": _SYSTEM}]
        for m in request.messages:
            messages.append({"role": m.role, "content": m.content})

        tools = _openai_tools()
        tools_called: list = []

        try:
            # Phase 1: tool-calling rounds (non-streaming)
            # Each tool event is sent immediately → Cloudflare stays alive
            for _ in range(5):
                response = client.chat.completions.create(
                    model="gemini-2.5-flash",
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                msg = response.choices[0].message

                if not msg.tool_calls:
                    # Phase 2: stream final text in small chunks (typewriter effect)
                    content = msg.content or ""
                    for i in range(0, len(content), 6):
                        yield _sse({"type": "text", "content": content[i:i + 6]})
                    break

                # Execute tools — yield one event per tool so connection stays warm
                messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id, "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    tools_called.append(tc.function.name)
                    yield _sse({"type": "tool", "name": tc.function.name})
                    args = json.loads(tc.function.arguments)
                    result = _execute_tool(tc.function.name, args, db)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

            yield _sse({"type": "done", "tools_called": tools_called})

        except RateLimitError as exc:
            body = exc.body or {}
            err_detail = body.get("error", {}) if isinstance(body, dict) else {}
            raw_msg = err_detail.get("message") or exc.message or str(exc)
            yield _sse({"type": "error", "message": (
                f"Limite de quota da API Gemini atingido: {raw_msg}. "
                "Verifica se a chave foi criada em aistudio.google.com com uma conta Gmail pessoal."
            )})
        except APIStatusError as exc:
            yield _sse({"type": "error", "message": f"Erro da API Gemini ({exc.status_code}): {exc.message}"})
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
