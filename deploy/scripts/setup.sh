#!/bin/bash
# setup.sh — prepara a VPS pro escala-freemium (one-time).
#
# Rode como root (ou via sudo):
#   sudo bash deploy/scripts/setup.sh
#
# Idempotente — pode rodar de novo sem quebrar nada.
# Assume Ubuntu 22.04/24.04 com Caddy já rodando (T&F + outros apps já no ar).

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log()  { echo -e "${GREEN}[setup]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC}  $*"; }
fail() { echo -e "${RED}[fail]${NC}  $*"; exit 1; }

[[ $EUID -eq 0 ]] || fail "Rode como root (sudo bash deploy/scripts/setup.sh)"

# ============================================================================
log "1/6 — Atualizando apt e instalando libs OS"
# ============================================================================
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq

# Libs do WeasyPrint (renderização de PDF)
apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-noto-color-emoji

# Build tools + git (se ainda não tiver)
apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    ca-certificates

# ============================================================================
log "2/6 — Verificando Node.js"
# ============================================================================
if ! command -v node >/dev/null 2>&1; then
    warn "Node não encontrado — instalando 20.x via NodeSource"
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi
NODE_VERSION=$(node --version)
log "Node: $NODE_VERSION"

# ============================================================================
log "3/6 — Verificando pnpm"
# ============================================================================
if ! command -v pnpm >/dev/null 2>&1; then
    warn "pnpm não encontrado — instalando global via npm"
    npm install -g pnpm
fi
log "pnpm: $(pnpm --version)"

# ============================================================================
log "4/6 — Usuário deploy"
# ============================================================================
if ! id deploy >/dev/null 2>&1; then
    warn "Usuário 'deploy' não existe — criando"
    useradd -m -s /bin/bash deploy
fi

# Diretório do app
mkdir -p /opt/escala-freemium
chown -R deploy:deploy /opt/escala-freemium

# /var/log/escala-freemium pro systemd ReadWritePaths
mkdir -p /var/log/escala-freemium
chown deploy:deploy /var/log/escala-freemium

# ============================================================================
log "5/6 — Verificando uv (Python pkg manager) pro user deploy"
# ============================================================================
if ! sudo -u deploy bash -c 'command -v $HOME/.local/bin/uv' >/dev/null 2>&1; then
    warn "uv não instalado pro user deploy — instalando"
    sudo -u deploy bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi
UV_VERSION=$(sudo -u deploy bash -c '$HOME/.local/bin/uv --version')
log "uv: $UV_VERSION"

# ============================================================================
log "6/6 — Verificando Caddy"
# ============================================================================
if ! systemctl is-active --quiet caddy; then
    warn "Caddy não está ativo. Você precisa de Caddy rodando antes do deploy."
    warn "Se não está instalado: https://caddyserver.com/docs/install"
fi

cat <<EOF

${GREEN}═══════════════════════════════════════════════════════${NC}
${GREEN}✓ SETUP CONCLUÍDO${NC}
${GREEN}═══════════════════════════════════════════════════════${NC}

Próximos passos:
  1. Adicione o DNS:
       A · simulaescala.mudacao.com.br → IP da VPS
  2. Clone o repo como deploy:
       sudo -u deploy -i
       cd /opt/escala-freemium
       git clone https://github.com/ffeldens/mudacao-escala.git .
  3. Crie o .env:
       cp .env.example .env
       nano .env   # preencher DATABASE_URL, RESEND_API_KEY, etc
  4. Rode o primeiro deploy:
       bash deploy/scripts/first-deploy.sh

EOF
