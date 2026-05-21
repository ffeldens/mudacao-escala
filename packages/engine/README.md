# engine — motor de cálculo

Pacote Python puro com a lógica core do escala-toolkit. Sem dependência de framework, DB ou rede.

## Responsabilidades

- `simulate(input)` → calcula impacto da migração 6x1 → 5x2 para 1 loja
- `validate_clt(schedule)` → valida uma escala contra a régua CLT vigente
- `calculate_coverage(...)` → calcula curva de cobertura horária
- `calculate_financial(...)` → calcula folha + encargos + benefícios

## Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Uso (CLI)

```bash
engine simulate --input tests/fixtures/shopping_m.json --scenario neutro
engine validate-clt --escala tests/fixtures/sample_schedule.json
```

## Uso (Python)

```python
from engine.core import simulate
from engine.models import SimulationInput
import json

data = json.load(open("tests/fixtures/shopping_m.json"))
result = simulate(SimulationInput(**data))
print(result.delta_folha_pct)
```

## Testes

```bash
pytest                        # todos
pytest tests/test_simulate.py # apenas simulate
pytest -k "shopping_m"        # filtro por fixture
pytest --cov=engine           # com cobertura
```

## Critérios de aceite (Fase 1A)

Ver `docs/PRD.md` seção 5.6 (AC-101 a AC-106).
