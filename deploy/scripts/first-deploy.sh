#!/bin/bash
# first-deploy.sh — primeiro deploy do escala-freemium.
#
# Rode como usuário 'deploy', com o repo já clonado em /opt/escala-freemium:
#   sudo -u deploy -i
#   cd /opt/escala-freemium
#   bash deploy/scripts/first-deploy.sh

set -euo pipefail

APP_DIR="/opt/escala-freemium"
DOMAIN="${DOMAIN:-simulaescala.mudacao.com.br}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC}   $*"; }
fail() { echo -e "${RED}[fail]${NC}   $*"; exit 1; }

# ============================================================================
# Validações
# ============================================================================
[[ $(whoami) == "deploy" ]] || fail "Rode como usuário 'deploy': sudo -u deploy -i"
[[ -d "$APP_DIR" ]] || fail "Diretório $APP_DIR não existe"
cd "$APP_DIR"

[[ -d ".git" ]] || fail "$APP_DIR não é um repo git"
[[ -f ".env" ]] || fail ".env não encontrado — copie .env.example e preencha"

# Garante uv e pnpm no PATH
export PATH="$HOME/.local/bin:$HOME/.local/share/pnpm:$PATH"
command -v uv >/dev/null || fail "uv não encontrado. Rode setup.sh primeiro."
command -v pnpm >/dev/null || fail "pnpm não encontrado. Rode setup.sh primeiro."

# Validações de .env
source .env
[[ -n "${DATABASE_URL:-}" ]] || fail "DATABASE_URL não está no .env"
[[ -n "${RESEND_API_KEY:-}" ]] || warn "RESEND_API_KEY vazia — emails não vão sair"

# ============================================================================
log "1/7 — uv sync (API + engine)"
# ============================================================================
cd "$APP_DIR/apps/api"
uv sync
cd "$APP_DIR"

# ============================================================================
log "2/7 — Smoke test: conectar Postgres + criar tabelas"
# ============================================================================
cd "$APP_DIR/apps/api"
set -a; source "$APP_DIR/.env"; set +a
uv run python -c "
import os
print(f'DATABASE_URL configurada: {bool(os.environ.get(\"DATABASE_URL\"))}')
from escala_freemium_api.db import init_db
init_db()
print('✓ Schema freemium + tabelas OK no Supabase')
"
cd "$APP_DIR"

# ============================================================================
log "3/7 — pnpm install + build (Web)"
# ============================================================================
cd "$APP_DIR/apps/web"
pnpm install --frozen-lockfile
# Carrega vars do .env (NEXT_PUBLIC_* sao bakeadas no bundle em build time)
set -a; source "$APP_DIR/.env"; set +a
pnpm build
cd "$APP_DIR"

# ============================================================================
log "4/7 — systemd units (API + Web)"
# ============================================================================
sudo cp "$APP_DIR/deploy/systemd/escala-freemium-api.service" \
    /etc/systemd/system/escala-freemium-api.service
sudo cp "$APP_DIR/deploy/systemd/escala-freemium-web.service" \
    /etc/systemd/system/escala-freemium-web.service
sudo systemctl daemon-reload
sudo systemctl enable escala-freemium-api escala-freemium-web

sudo systemctl restart escala-freemium-api
sleep 3
sudo systemctl is-active --quiet escala-freemium-api || {
    sudo journalctl -u escala-freemium-api -n 40 --no-pager
    fail "API não subiu"
}
log "✓ API ativa"

sudo systemctl restart escala-freemium-web
sleep 4
sudo systemctl is-active --quiet escala-freemium-web || {
    sudo journalctl -u escala-freemium-web -n 40 --no-pager
    fail "Web não subiu"
}
log "✓ Web ativa"

# ============================================================================
log "5/7 — Healthcheck loopback"
# ============================================================================
curl -fsS http://127.0.0.1:8012/api/health >/dev/null || fail "API :8012 não responde"
log "✓ API loopback :8012 → 200"

curl -fsS http://127.0.0.1:8011 >/dev/null || fail "Web :8011 não responde"
log "✓ Web loopback :8011 → 200"

# ============================================================================
log "6/7 — Caddy snippet"
# ============================================================================
SNIPPET="$APP_DIR/deploy/Caddyfile.snippet"
CADDYFILE="/etc/caddy/Caddyfile"

if grep -q "$DOMAIN" "$CADDYFILE" 2>/dev/null; then
    log "Bloco do $DOMAIN já existe no Caddyfile — pulando"
else
    warn "Adicionando bloco do $DOMAIN ao Caddyfile..."
    echo "" | sudo tee -a "$CADDYFILE" >/dev/null
    cat "$SNIPPET" | sudo tee -a "$CADDYFILE" >/dev/null
fi

# Valida e recarrega
sudo caddy validate --config "$CADDYFILE" || fail "Caddyfile inválido"
sudo systemctl reload caddy
log "✓ Caddy recarregado"

# ============================================================================
log "7/7 — Teste HTTPS público"
# ============================================================================
sleep 3  # pequena pausa pra Caddy emitir cert se ainda não tem
if curl -fsS -m 10 "https://${DOMAIN}/api/health" 2>/dev/null | grep -q '"status":"ok"'; then
    log "✓ https://${DOMAIN}/api/health → 200"
else
    warn "https://${DOMAIN}/api/health ainda não respondeu — Caddy pode estar emitindo cert."
    warn "Aguarda 30s e tenta: curl https://${DOMAIN}/api/health"
fi

cat <<EOF

${GREEN}═══════════════════════════════════════════════════════${NC}
${GREEN}✓ DEPLOY CONCLUÍDO${NC}
${GREEN}═══════════════════════════════════════════════════════${NC}

App no ar em: ${GREEN}https://${DOMAIN}${NC}

Comandos úteis:
  Logs API:        sudo journalctl -u escala-freemium-api -f
  Logs Web:        sudo journalctl -u escala-freemium-web -f
  Logs Caddy:      sudo journalctl -u caddy -f
  Restart API:     sudo systemctl restart escala-freemium-api
  Restart Web:     sudo systemctl restart escala-freemium-web
  Update código:   bash deploy/scripts/update.sh

EOF
