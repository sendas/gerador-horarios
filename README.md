# Gerador de Horários Escolares

Aplicação web para geração automática de horários escolares para agrupamentos com até 3 escolas.

## Stack

- **Backend**: FastAPI + OR-Tools CP-SAT + SQLite (SQLAlchemy)
- **Frontend**: Vue 3 + Quasar Framework + TypeScript + Pinia

## Funcionalidades

- Gestão de agrupamentos, escolas, anos letivos
- Configuração de tempos letivos por dia
- Gestão de salas, disciplinas, turmas
- Currículo por turma (horas/semana por disciplina)
- Gestão de professores (disponibilidade, escolas, disciplinas)
- Serviço não letivo
- **Geração automática de horários** com OR-Tools CP-SAT
  - Restrições hard: sem sobreposições, disponibilidade, viagens entre escolas
  - Restrições soft: dia livre preferido, máximo de aulas por dia
- Exportação: HTML, CSV, Excel
- Visualização por turma, professor ou sala

## Início Rápido

### Com Docker Compose

```bash
docker-compose up
```

Frontend: http://localhost:9000  
Backend API: http://localhost:8000  
Docs API: http://localhost:8000/docs

### Desenvolvimento Local

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

## Estrutura

```
gerador-horarios/
├── backend/
│   ├── app/
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── routers/      # FastAPI routers (CRUD)
│   │   ├── scheduler/    # OR-Tools CP-SAT engine
│   │   ├── exports/      # HTML/CSV/Excel exporters
│   │   ├── database.py
│   │   └── main.py
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/        # Vue pages
        ├── stores/       # Pinia stores
        ├── components/   # Reusable components
        ├── router/       # Vue Router
        └── layouts/      # App layouts
```

## Modelos de Dados

- **Cluster** → agrupamento de escolas
- **School** → escola dentro de um agrupamento
- **AcademicYear** → ano letivo
- **TimeSlotConfig** → configuração dos tempos letivos
- **Room** → sala de aula
- **Subject** → disciplina
- **Class** → turma
- **CurriculumEntry** → horas semanais de cada disciplina por turma
- **Teacher** → professor
- **TeacherSchoolAssignment** → escolas onde leciona + tempo de viagem
- **TeacherAvailability** → disponibilidade horária do professor
- **Timetable** → horário gerado
- **ScheduledLesson** → cada aula agendada no horário
- **NonTeachingType** → tipo de serviço não letivo
- **NonTeachingAssignment** → atribuição de serviço não letivo a professor
