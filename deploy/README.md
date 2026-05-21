# Deploy — MudAção Escala Freemium

Guia de deploy na VPS Hostinger (mesma do T&F Escala, processos isolados).

## Portas (manter atualizado)

| App | Porta | Domínio |
|---|---|---|
| ideias | 8000 | ideias.mudacao.com.br |
| gtp | 8001 | gtp.mudacao.com.br |
| intel | 8002 | intel.mudacao.com.br |
| upload | 8003 | upload.mudacao.com.br |
| T&F Escala (privado) | 8010 | escala.mudacao.com.br |
| **Escala Freemium API** | **8012** | (loopback) |
| **Escala Freemium Web** | **8011** | **simulaescala.mudacao.com.br** |

## Pré-requisitos (já feitos na VPS)

- Ubuntu 24.04 + usuário `deploy` + uv + Caddy + Node 20
- Supabase com schema `freemium` (será criado automaticamente no startup)

## Setup inicial (1×)

```bash
# 1. DNS
# Painel Hostinger → A record: simulaescala → 31.97.163.175

# 2. Clone na VPS
sudo -u deploy -i
sudo mkdir -p /opt/escala-freemium && sudo chown deploy:deploy /opt/escala-freemium
cd /opt/escala-freemium
git clone git@github.com:SEU-USUARIO/mudacao-escala.git .

# 3. .env
cp .env.example .env
nano .env   # preencher DATABASE_URL, RESEND_API_KEY, etc

# 4. Instalar deps
cd apps/api && uv sync && cd /opt/escala-freemium
cd apps/web && pnpm install && pnpm build && cd /opt/escala-freemium

# 5. Systemd
sudo cp deploy/systemd/escala-freemium-api.service /etc/systemd/system/
sudo cp deploy/systemd/escala-freemium-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now escala-freemium-api escala-freemium-web

# 6. Caddy
sudo cat deploy/Caddyfile.snippet >> /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## Updates subsequentes

```bash
ssh deploy@31.97.163.175
cd /opt/escala-freemium
bash deploy/scripts/update.sh
```

## Logs

```bash
sudo journalctl -u escala-freemium-api -f
sudo journalctl -u escala-freemium-web -f
sudo tail -f /var/log/caddy/simulaescala.access.log
```
