#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

# ── Cores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[AVISO]${NC} $*"; }
error()   { echo -e "${RED}[ERRO]${NC}  $*"; exit 1; }

# ── Cabeçalho ────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      Gerador de Horários — Deploy        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Pré-requisitos ───────────────────────────────────────────────────────────
info "A verificar pré-requisitos..."

command -v docker  >/dev/null 2>&1 || error "Docker não encontrado. Instala o Docker primeiro."
command -v git     >/dev/null 2>&1 || error "Git não encontrado."

COMPOSE_CMD=""
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    error "Docker Compose não encontrado."
fi
success "Docker e Compose encontrados ($COMPOSE_CMD)"

# ── Ficheiro .env ────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    warn "Ficheiro .env criado a partir do .env.example. Podes editar antes de continuar."
    warn "  APP_PORT=61100  →  porta de acesso no NAS"
    echo ""
fi

# ── Carregar variáveis ────────────────────────────────────────────────────────
set -o allexport; source .env; set +o allexport
APP_PORT="${APP_PORT:-61100}"

# ── Pasta de dados ────────────────────────────────────────────────────────────
info "A preparar pasta de dados..."
mkdir -p data
success "Pasta ./data/ pronta (base de dados SQLite persistida aqui)"

# ── Actualizar código (se já existe instalação) ──────────────────────────────
if git remote -v 2>/dev/null | grep -q origin; then
    info "A actualizar código do repositório..."
    git pull origin "$(git branch --show-current)" --ff-only 2>/dev/null || warn "Não foi possível actualizar (continua com versão local)"
fi

# ── Build e arranque ─────────────────────────────────────────────────────────
info "A construir imagens Docker..."
$COMPOSE_CMD build --no-cache

info "A iniciar serviços..."
$COMPOSE_CMD up -d

# ── Aguardar backend ─────────────────────────────────────────────────────────
info "A aguardar que o backend fique disponível..."
RETRIES=20
until docker inspect --format='{{.State.Health.Status}}' \
      "$(${COMPOSE_CMD} ps -q backend 2>/dev/null)" 2>/dev/null | grep -q "healthy" || [ $RETRIES -eq 0 ]; do
    sleep 3
    RETRIES=$((RETRIES - 1))
    echo -n "."
done
echo ""

if [ $RETRIES -eq 0 ]; then
    warn "O backend ainda não respondeu (pode ainda estar a arrancar). Verifica com:"
    warn "  $COMPOSE_CMD logs backend"
else
    success "Backend disponível"
fi

# ── Estado final ─────────────────────────────────────────────────────────────
echo ""
$COMPOSE_CMD ps
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Gerador de Horários está disponível!   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}URL:${NC}      http://$(hostname -I | awk '{print $1}'):${APP_PORT}"
echo -e "  ${BLUE}API Docs:${NC} http://$(hostname -I | awk '{print $1}'):${APP_PORT}/api/v1/docs  (via proxy → 404 aqui)"
echo ""
echo -e "  Logs:    ${YELLOW}$COMPOSE_CMD logs -f${NC}"
echo -e "  Parar:   ${YELLOW}$COMPOSE_CMD down${NC}"
echo -e "  Backup:  ${YELLOW}cp data/gerador_horarios.db data/backup_\$(date +%Y%m%d).db${NC}"
echo ""
