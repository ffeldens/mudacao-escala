#!/bin/bash
# update.sh — atualiza app pra última versão do main
#
# Rode como usuário 'deploy':
#   sudo -u deploy -i
#   cd /opt/escala-freemium
#   bash deploy/scripts/update.sh

set -euo pipefail

APP_DIR="/opt/escala-freemium"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
log()  { echo -e "${GREEN}[update]${NC} $*"; }
fail() { echo -e "${RED}[fail]${NC}   $*"; exit 1; }

[[ $(whoami) == "deploy" ]] || fail "Rode como usuário 'deploy'"
cd "$APP_DIR"

export PATH="$HOME/.local/bin:$HOME/.local/share/pnpm:$PATH"

log "1/5 — git pull"
git fetch --all
git reset --hard origin/main

log "2/5 — uv sync (API + engine)"
cd apps/api && uv sync && cd "$APP_DIR"

log "3/5 — pnpm install + build (Web)"
cd "$APP_DIR/apps/web"
pnpm install --frozen-lockfile
# Carrega vars do .env (NEXT_PUBLIC_* sao bakeadas no bundle em build time)
set -a; source "$APP_DIR/.env"; set +a
pnpm build
cd "$APP_DIR"

log "4/5 — Restart API"
sudo systemctl restart escala-freemium-api
sleep 3
sudo systemctl is-active --quiet escala-freemium-api || fail "API não subiu"

log "5/5 — Restart Web"
sudo systemctl restart escala-freemium-web
sleep 3
sudo systemctl is-active --quiet escala-freemium-web || fail "Web não subiu"

# Healthcheck com retry — uv + conexão Supabase pode levar até 10s no startup
log "Healthcheck (até 15s)..."
for i in {1..15}; do
    if curl -fsS http://127.0.0.1:8012/api/health >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
curl -fsS http://127.0.0.1:8012/api/health >/dev/null || fail "API healthcheck falhou"
curl -fsS http://127.0.0.1:8011 >/dev/null || fail "Web healthcheck falhou"

log "✓ App atualizado e rodando"
