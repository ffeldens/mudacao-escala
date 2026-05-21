# escala-freemium-api

API FastAPI que expõe o engine `escala-engine` via HTTP.

## Rotas

| Método | Caminho | O que faz |
|---|---|---|
| GET | `/api/health` | Healthcheck |
| GET | `/api/version` | Versão do app + engine |
| POST | `/api/simulate` | Roda simulação (anônimo) |
| POST | `/api/lead` | Captura lead + dispara email |
| POST | `/api/lead-and-simulate` | Atalho: simula + persiste lead + envia email com PDF |

Docs interativos: `http://localhost:8012/docs`

## Dev local

```bash
cd apps/api
uv sync
cp ../../.env.example ../../.env  # preencher DATABASE_URL + RESEND_API_KEY
uv run uvicorn escala_freemium_api.main:app --reload --port 8012
```

## Testes

```bash
uv run pytest
```
