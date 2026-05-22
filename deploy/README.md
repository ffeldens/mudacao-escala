# Deploy — MudAção Escala Freemium

Guia de deploy na VPS Hostinger (mesma do T&F Escala, processos isolados).

## Portas dos apps na VPS

| App | Porta | Domínio |
|---|---|---|
| ideias | 8000 | ideias.mudacao.com.br |
| gtp | 8001 | gtp.mudacao.com.br |
| intel | 8002 | intel.mudacao.com.br |
| upload | 8003 | upload.mudacao.com.br |
| T&F Escala (privado) | 8010 | escala.mudacao.com.br |
| **Escala Freemium API** | **8012** | (loopback) |
| **Escala Freemium Web** | **8011** | **simulaescala.mudacao.com.br** |

---

## Pré-requisitos

Antes de começar:

- [ ] Repo no GitHub atualizado (`git push` de todos os commits locais)
- [ ] DNS adicionado: `simulaescala.mudacao.com.br` → `31.97.163.175` (A record na Hostinger)
- [ ] Resend: API key válida + (opcional) domínio `mudacao.com.br` validado
- [ ] Connection string do Supabase em mãos (a mesma do T&F, schema `freemium` será criado automaticamente)

> Aguarde 1-5 min após criar o DNS antes de fazer o deploy — o Caddy precisa resolver o domínio pra emitir o cert Let's Encrypt.

---

## Procedimento de deploy (do zero)

### 1. Setup da VPS (one-time, como root)

```bash
ssh root@31.97.163.175

# Clona temporariamente só pra pegar o script
git clone https://github.com/ffeldens/mudacao-escala.git /tmp/mudacao-escala
sudo bash /tmp/mudacao-escala/deploy/scripts/setup.sh
rm -rf /tmp/mudacao-escala
```

O `setup.sh` é idempotente — pode rodar de novo sem quebrar. Ele:
- Instala libs OS pro WeasyPrint (libpango, libcairo, libgdk-pixbuf, fonts)
- Garante Node 20, pnpm e uv instalados
- Cria usuário `deploy` (se não existir) e diretório `/opt/escala-freemium`

### 2. Clone do repo + .env (como usuário deploy)

```bash
sudo -u deploy -i
cd /opt/escala-freemium
git clone https://github.com/ffeldens/mudacao-escala.git .

# .env
cp .env.example .env
nano .env
```

Preenche no `.env`:

```env
APP_ENV=production
APP_BASE_URL=https://simulaescala.mudacao.com.br

DATABASE_URL=postgresql+psycopg://postgres.PROJREF:SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres

RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=simulador@mudacao.com.br   # ou onboarding@resend.dev se domínio não validado
RESEND_REPLY_TO=felipe@feldens.com
ADMIN_NOTIFY_EMAIL=felipe@feldens.com
```

### 3. Primeiro deploy

```bash
bash deploy/scripts/first-deploy.sh
```

Esse script faz tudo:
1. `uv sync` (API + engine)
2. Smoke test: conecta no Supabase e cria as tabelas do schema `freemium`
3. `pnpm install --frozen-lockfile` + `pnpm build` (Web)
4. Instala e inicia systemd units (`escala-freemium-api`, `escala-freemium-web`)
5. Healthcheck em loopback (`:8011` e `:8012`)
6. Adiciona o bloco do Caddyfile pro `simulaescala.mudacao.com.br`
7. Reload Caddy → emite cert SSL via Let's Encrypt
8. Healthcheck público em HTTPS

**Demora ~3-5 min** na primeira vez (download deps + build Next + emissão cert).

### 4. Validação

No browser: **https://simulaescala.mudacao.com.br**

Faça uma simulação real com seu email pra confirmar:
- ✅ Form funciona
- ✅ Resultado aparece
- ✅ Email do lead chega
- ✅ Email admin notification chega

---

## Updates subsequentes

Toda vez que houver mudança no código no GitHub:

```bash
ssh deploy@31.97.163.175
cd /opt/escala-freemium
bash deploy/scripts/update.sh
```

Esse script faz:
1. `git pull` (origin/main, reset hard)
2. `uv sync` (atualiza deps Python se mudou)
3. `pnpm install --frozen-lockfile && pnpm build` (rebuilda Next se mudou)
4. `systemctl restart` API + Web
5. Healthcheck

Total: ~30s a 2 min dependendo do que mudou.

---

## Logs e debug

| O quê | Comando |
|---|---|
| Logs API em tempo real | `sudo journalctl -u escala-freemium-api -f` |
| Logs Web em tempo real | `sudo journalctl -u escala-freemium-web -f` |
| Logs Caddy | `sudo journalctl -u caddy -f` |
| Últimos 50 logs API | `sudo journalctl -u escala-freemium-api -n 50 --no-pager` |
| Status dos services | `sudo systemctl status escala-freemium-api escala-freemium-web` |
| Restart API | `sudo systemctl restart escala-freemium-api` |
| Restart Web | `sudo systemctl restart escala-freemium-web` |
| Reload Caddy | `sudo systemctl reload caddy` |
| Validar Caddyfile | `sudo caddy validate --config /etc/caddy/Caddyfile` |

Leads e simulações aparecem no painel Supabase em **Table Editor** → schema `freemium`.

---

## Troubleshooting

### "API não responde em :8012"
```bash
sudo journalctl -u escala-freemium-api -n 50 --no-pager
```
- `DATABASE_URL` errada no `.env` → conexão Supabase falha no startup
- Porta 8012 ocupada → `sudo lsof -i :8012`

### "502 Bad Gateway no browser"
- Service caiu: `sudo systemctl status escala-freemium-web`
- Caddy aponta pra porta errada: confere o bloco no `/etc/caddy/Caddyfile`

### "SSL fail / cert não emitido"
- DNS não propagou ainda: `dig +short simulaescala.mudacao.com.br`
- Firewall bloqueia 80/443: `sudo ufw status`
- Log: `sudo journalctl -u caddy -n 50 --no-pager`

### "Email não chega"
- Variáveis Resend no .env: `grep RESEND /opt/escala-freemium/.env`
- Service usou o .env certo: `sudo systemctl show escala-freemium-api | grep EnvironmentFile`
- Logs API: procura por `Resend retornou` ou `RESEND_API_KEY vazia`
- Dashboard Resend: https://resend.com/emails

### "PDF não vem anexo"
- WeasyPrint dep faltando: `sudo apt list --installed 2>/dev/null | grep -E "libpango|libcairo"`
- Roda o setup.sh de novo: `sudo bash /opt/escala-freemium/deploy/scripts/setup.sh`

---

## Reverter / Desinstalar

```bash
sudo systemctl stop escala-freemium-api escala-freemium-web
sudo systemctl disable escala-freemium-api escala-freemium-web
sudo rm /etc/systemd/system/escala-freemium-{api,web}.service
sudo systemctl daemon-reload

# Remove o bloco do Caddyfile manualmente, depois:
sudo systemctl reload caddy

sudo rm -rf /opt/escala-freemium
```

Os leads continuam no Supabase. Pra apagar tudo: drop do schema `freemium` no SQL Editor do Supabase.
