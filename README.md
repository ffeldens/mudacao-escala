# MudAção Escala — Simulador Freemium PEC 8/2025

Simulador gratuito de impacto da PEC 8/2025 (transição 6x1 → 5x2) para varejo e food service.

> **Objetivo**: capturar leads mostrando quanto sua rede vai gastar com a nova lei — e como uma ferramenta inteligente de escala pode economizar.

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js 14 (App Router) + Tailwind + shadcn/ui |
| API | FastAPI + psycopg |
| Engine | Python (reaproveitado do T&F Escala) |
| DB | Supabase (Postgres, schema `freemium`) |
| Auth | Supabase Auth (magic link) — só pra tier pago |
| Email | Resend (DKIM já configurado em mudacao.com.br) |
| Pagamento | Stripe (Sprint 2) |
| Hosting | VPS Hostinger + Caddy reverse proxy |
| Domain | `simulaescala.mudacao.com.br` |

## Arquitetura

```
Internet
  ↓ DNS: simulaescala.mudacao.com.br → 31.97.163.175
  ↓
Caddy :443 (Let's Encrypt automático)
  ↓
Next.js :8011 (systemd, Node runtime)
  ↓ /api/simulate (rota interna proxy)
FastAPI :8012 (systemd, loopback, engine wrapper)
  ↓
Supabase Postgres (schema "freemium")
  + Resend (email + PDF do resultado)
```

## Estrutura

```
.
├── apps/
│   ├── web/                 ← Next.js 14 (landing + simulador + pricing)
│   └── api/                 ← FastAPI engine wrapper
├── packages/
│   └── engine/              ← Python engine (cópia do T&F Escala)
├── deploy/                  ← Caddyfile snippet, systemd, scripts
└── README.md
```

## Dev local

```bash
# Pré-req: Node 20+, pnpm, Python 3.11+, uv

# Frontend
cd apps/web
pnpm install
cp .env.local.example .env.local  # preencher Supabase + Resend keys
pnpm dev                          # http://localhost:3000

# Backend (em outro terminal)
cd apps/api
uv sync
uv run uvicorn escala_freemium_api.main:app --reload --port 8012
```

## Deploy

```bash
ssh deploy@31.97.163.175
cd /opt/escala-freemium
bash deploy/scripts/update.sh
```

Veja [`deploy/README.md`](deploy/README.md) pra setup inicial.

## MVP (1 semana)

| Dia | Entregável |
|---|---|
| D1 | Scaffold + engine wrapper rodando local |
| D2 | Landing SEO |
| D3 | Form simulador + gate lead capture |
| D4 | Resultado com 3 cenários + extrapolação rede |
| D5 | Resend email + PDF + página /precos |
| D6 | Deploy em produção |
| D7 | Polimento + soft launch |

**Meta:** 100 emails capturados em 30 dias.

## Roadmap pós-MVP

- Sprint 2: Stripe checkout + auth real + dashboard usuário
- Sprint 3: Multi-loja paga + import CSV
- Sprint 4: Planejador automático (CSP solver)
- Sprint 5: Validador CLT PDF + auditoria jurídica

---

**Mantenedor:** Felipe Feldens · MudAção · felipe@feldens.com
