"""Gerador de rede sintética de N lojas para análise multi-loja (Fase 1D).

Permite executar simulações em escala (10, 50, 343 lojas) sem depender de
dados reais. Cada loja gerada tem perfil plausível baseado em mix configurável
de marcas (T&F vs TFC), tipos (shopping, rua, outlet) e clusters (PP, P, M, G).

A geração é determinística por semente — útil para reprodutibilidade em demos
e benchmarks. Estados brasileiros e nomes de shoppings são amostrados de uma
lista pré-definida (sem dados reais de cliente).
"""

from __future__ import annotations

import hashlib
import random
from decimal import Decimal

from engine.models import (
    Brand,
    FunctionRole,
    SimulationInput,
    StoreCluster,
    StoreInput,
    StoreType,
)
from engine.synthetic_demand import CLUSTER_FACTORS

# =============================================================================
# Pools de nomes para gerar lojas plausíveis sem dados reais
# =============================================================================
_ESTADOS = ["SP", "RJ", "MG", "RS", "SC", "PR", "BA", "PE", "DF", "GO", "CE", "ES"]
_SHOPPINGS = [
    "JK", "Iguatemi", "Morumbi", "Eldorado", "Vila Olímpia", "Pátio Higienópolis",
    "Anália Franco", "Ibirapuera", "BarraShopping", "RioSul", "NorteShopping",
    "Boulevard", "Diamond", "Pátio Brasil", "Park", "Plaza", "Galleria", "Center",
    "Praia de Belas", "Moinhos", "DiamondMall", "Pátio Savassi",
]
_RUAS = [
    "Oscar Freire", "Augusta", "Garcia D'Ávila", "Visconde de Pirajá",
    "Lima Barreto", "Padre Chagas", "Moinhos de Vento", "São Bento",
    "Ana Costa", "Marechal Floriano",
]


# =============================================================================
# Distribuições típicas por tipo+cluster
# =============================================================================
def _headcount_t_f(cluster: StoreCluster) -> dict[str, int]:
    """Headcount típico para uma loja Track & Field por cluster."""
    return {
        "PP": {"vendedor": 3, "caixa": 1, "estoque": 1, "gerencia": 1},
        "P":  {"vendedor": 5, "caixa": 1, "estoque": 1, "gerencia": 2},
        "M":  {"vendedor": 8, "caixa": 2, "estoque": 1, "gerencia": 2},
        "G":  {"vendedor": 14, "caixa": 3, "estoque": 2, "gerencia": 3},
    }[cluster]


def _headcount_tfc(cluster: StoreCluster) -> dict[str, int]:
    """Headcount típico para um café TFC por cluster."""
    return {
        "PP": {"atendente": 2, "barista": 2, "gerencia": 1},
        "P":  {"atendente": 4, "barista": 3, "gerencia": 1},
        "M":  {"atendente": 6, "barista": 4, "gerencia": 1},
        "G":  {"atendente": 9, "barista": 6, "gerencia": 2},
    }[cluster]


def _faturamento_t_f(cluster: StoreCluster, tipo: StoreType) -> Decimal:
    """Faturamento mensal típico (R$) para varejo de moda esportiva."""
    base = {"PP": 180_000, "P": 280_000, "M": 450_000, "G": 780_000}[cluster]
    if tipo == "rua":
        base = int(base * 0.75)
    elif tipo == "outlet":
        base = int(base * 0.65)
    return Decimal(str(base))


def _faturamento_tfc(cluster: StoreCluster) -> Decimal:
    base = {"PP": 90_000, "P": 180_000, "M": 320_000, "G": 580_000}[cluster]
    return Decimal(str(base))


_SALARIOS_T_F = {
    "vendedor": Decimal("2200"),
    "caixa": Decimal("2000"),
    "estoque": Decimal("1900"),
    "gerencia": Decimal("5500"),
}
_SALARIOS_TFC = {
    "atendente": Decimal("1900"),
    "barista": Decimal("2300"),
    "gerencia": Decimal("4800"),
}


# =============================================================================
# Geração de uma loja
# =============================================================================
def generate_store(
    *,
    brand: Brand,
    cluster: StoreCluster,
    tipo: StoreType,
    codigo: str,
    nome: str,
    rng: random.Random,
) -> StoreInput:
    """Gera um StoreInput sintético plausível."""
    # Variação salarial: ±5% por cluster (lojas G pagam um pouco mais)
    multiplicador_salario = {"PP": 0.95, "P": 0.97, "M": 1.00, "G": 1.05}[cluster]

    if brand == "track_field":
        headcount = _headcount_t_f(cluster)
        salarios = _SALARIOS_T_F
        faturamento = _faturamento_t_f(cluster, tipo)
        funcoes = [
            FunctionRole(
                nome="Vendedor",
                qtd_atual=headcount["vendedor"],
                salario_medio=(salarios["vendedor"] * Decimal(str(multiplicador_salario))).quantize(Decimal("0.01")),
                comissionado=True,
                presenca_minima_simultanea=2 if cluster in ("M", "G") else 1,
                restricoes_folga_estruturais=["sabado"],
            ),
            FunctionRole(
                nome="Caixa",
                qtd_atual=headcount["caixa"],
                salario_medio=(salarios["caixa"] * Decimal(str(multiplicador_salario))).quantize(Decimal("0.01")),
                comissionado=False,
                presenca_minima_simultanea=1,
            ),
            FunctionRole(
                nome="Estoque",
                qtd_atual=headcount["estoque"],
                salario_medio=(salarios["estoque"] * Decimal(str(multiplicador_salario))).quantize(Decimal("0.01")),
                comissionado=False,
                presenca_minima_simultanea=1,
            ),
            FunctionRole(
                nome="Gerencia",
                qtd_atual=headcount["gerencia"],
                salario_medio=(salarios["gerencia"] * Decimal(str(multiplicador_salario))).quantize(Decimal("0.01")),
                comissionado=False,
                presenca_minima_simultanea=1,
                pode_cobrir_funcoes=["Caixa", "Estoque"],  # multifunção T&F
            ),
        ]
        hora_abertura = 10 if tipo == "shopping" else 9
        hora_fechamento = 22 if tipo == "shopping" else 19
        dias_op = 7 if tipo == "shopping" else 6
    else:  # tfc
        headcount = _headcount_tfc(cluster)
        salarios = _SALARIOS_TFC
        faturamento = _faturamento_tfc(cluster)
        funcoes = [
            FunctionRole(
                nome="Atendente",
                qtd_atual=headcount["atendente"],
                salario_medio=(salarios["atendente"] * Decimal(str(multiplicador_salario))).quantize(Decimal("0.01")),
                comissionado=False,
            ),
            FunctionRole(
                nome="Barista",
                qtd_atual=headcount["barista"],
                salario_medio=(salarios["barista"] * Decimal(str(multiplicador_salario))).quantize(Decimal("0.01")),
                comissionado=False,
                pode_cobrir_funcoes=["Atendente"],
            ),
            FunctionRole(
                nome="Gerencia",
                qtd_atual=headcount["gerencia"],
                salario_medio=(salarios["gerencia"] * Decimal(str(multiplicador_salario))).quantize(Decimal("0.01")),
                comissionado=False,
                pode_cobrir_funcoes=["Atendente", "Barista"],
            ),
        ]
        hora_abertura = 8
        hora_fechamento = 22
        dias_op = 7

    return StoreInput(
        codigo=codigo,
        nome=nome,
        brand=brand,
        tipo=tipo,
        cluster=cluster,
        hora_abertura=hora_abertura,
        hora_fechamento=hora_fechamento,
        dias_operacao_semana=dias_op,
        faturamento_mensal=faturamento,
        ticket_history=[],
        funcoes=funcoes,
    )


# =============================================================================
# Geração de uma rede de N lojas
# =============================================================================
def generate_synthetic_network(
    *,
    n_lojas: int,
    brand_mix: dict[str, float] | None = None,
    cluster_mix: dict[str, float] | None = None,
    tipo_mix: dict[str, float] | None = None,
    semente: str = "default",
) -> list[SimulationInput]:
    """Gera N lojas sintéticas como SimulationInputs prontos para simulate().

    Args:
        n_lojas: número de lojas a gerar (1+).
        brand_mix: proporção de marcas. Default {track_field: 0.85, tfc: 0.15}
                   refletindo o mix real Track & Field (343 lojas + cafés).
        cluster_mix: proporção de clusters. Default refletindo curva normal:
                     {PP: 0.10, P: 0.30, M: 0.45, G: 0.15}.
        tipo_mix: para T&F, proporção shopping/rua/outlet.
                  Default {shopping: 0.75, rua: 0.20, outlet: 0.05}.
        semente: torna a geração determinística.

    Returns:
        Lista de SimulationInput, cada um pronto para passar a simulate().
    """
    if n_lojas < 1:
        raise ValueError("n_lojas deve ser ≥1")

    rng = random.Random(_seed(semente, str(n_lojas)))
    brand_mix = brand_mix or {"track_field": 0.85, "tfc": 0.15}
    cluster_mix = cluster_mix or {"PP": 0.10, "P": 0.30, "M": 0.45, "G": 0.15}
    tipo_mix = tipo_mix or {"shopping": 0.75, "rua": 0.20, "outlet": 0.05}

    inputs: list[SimulationInput] = []
    for i in range(n_lojas):
        brand = _weighted_choice(rng, brand_mix)
        cluster = _weighted_choice(rng, cluster_mix)
        # TFC só faz sentido em shopping
        if brand == "tfc":
            tipo = "shopping"
        else:
            tipo = _weighted_choice(rng, tipo_mix)

        # Nome plausível
        estado = rng.choice(_ESTADOS)
        if tipo == "shopping":
            nome_local = rng.choice(_SHOPPINGS)
            local_str = f"{nome_local} Shopping"
        else:
            local_str = rng.choice(_RUAS)

        prefixo = "TFC" if brand == "tfc" else "TF"
        codigo = f"{prefixo}-{estado}-{i+1:04d}"
        nome = f"{'TFC Café' if brand == 'tfc' else 'Track & Field'} — {local_str}"

        store = generate_store(
            brand=brand,  # type: ignore[arg-type]
            cluster=cluster,  # type: ignore[arg-type]
            tipo=tipo,  # type: ignore[arg-type]
            codigo=codigo,
            nome=nome,
            rng=rng,
        )

        inputs.append(SimulationInput(
            store=store,
            clt_version="2026-04",
            brand_rules_version=f"{brand.replace('_', '-')}-1.0.0",
        ))

    return inputs


def _weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    """Amostra uma chave do dict pesos por probabilidade."""
    keys = list(weights.keys())
    values = list(weights.values())
    return rng.choices(keys, weights=values, k=1)[0]


def _seed(*parts: str) -> int:
    return int(hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()[:8], 16)
