"""Ranking de candidatas a piloto da migração 6x1 → 5x2.

Pondera 4 fatores com pesos transparentes (ver AC-403 do PRD):
  1. **Tamanho típico** (cluster M+G > P+PP) — piloto mais representativo
  2. **Representatividade do mix** (shopping > rua, T&F > TFC se T&F é cliente)
  3. **Impacto médio** (delta_folha_pct mediano da rede; lojas próximas da
     mediana são preferíveis para extrapolar resultados)
  4. **Facilidade operacional** (proxy: # FTEs total; lojas com 8-15 FTEs
     são mais fáceis de pilotar — nem grandes demais, nem pequenas demais)

Cada fator gera uma nota 0-100. Score final = média ponderada (default
pesos iguais). Output inclui justificativa por loja para transparência.
"""

from __future__ import annotations

from decimal import Decimal
from statistics import median
from typing import Any

from engine.models import SimulationInput, SimulationOutput

# =============================================================================
# Pesos default (somam 1.0)
# =============================================================================
PESOS_DEFAULT = {
    "tamanho": 0.25,
    "representatividade": 0.25,
    "impacto_medio": 0.30,
    "facilidade": 0.20,
}


def rank_candidatas_piloto(
    *,
    simulacoes: list[tuple[SimulationInput, SimulationOutput]],
    top_k: int = 5,
    pesos: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Ranqueia lojas como candidatas a piloto.

    Args:
        simulacoes: lista de tuplas (input, output) de N lojas já simuladas.
        top_k: quantidade a retornar.
        pesos: dict com chaves 'tamanho', 'representatividade', 'impacto_medio',
               'facilidade'. Default: 0.25, 0.25, 0.30, 0.20.

    Returns:
        Lista ordenada por score desc com:
        - codigo, nome, brand, cluster, tipo
        - notas: dict com 4 notas 0-100
        - score: média ponderada 0-100
        - explicacao: list[str] motivos por que essa loja foi escolhida
    """
    if not simulacoes:
        return []

    pesos = pesos or PESOS_DEFAULT
    deltas_pct = [float(o.delta_folha_pct) for _, o in simulacoes]
    delta_mediano = median(deltas_pct)

    candidatas: list[dict[str, Any]] = []
    for inp, out in simulacoes:
        nota_tamanho = _nota_tamanho(inp.store.cluster)
        nota_repr = _nota_representatividade(inp.store.brand, inp.store.tipo)
        nota_impacto = _nota_impacto_medio(float(out.delta_folha_pct), delta_mediano)
        nota_facilidade = _nota_facilidade(float(out.fte_atual_total))

        score = (
            pesos["tamanho"] * nota_tamanho
            + pesos["representatividade"] * nota_repr
            + pesos["impacto_medio"] * nota_impacto
            + pesos["facilidade"] * nota_facilidade
        )

        explicacao = _explicar(
            cluster=inp.store.cluster,
            brand=inp.store.brand,
            tipo=inp.store.tipo,
            delta_pct=float(out.delta_folha_pct),
            delta_mediano=delta_mediano,
            fte_total=float(out.fte_atual_total),
        )

        candidatas.append({
            "codigo": inp.store.codigo,
            "nome": inp.store.nome,
            "brand": inp.store.brand,
            "cluster": inp.store.cluster,
            "tipo": inp.store.tipo,
            "fte_atual_total": float(out.fte_atual_total),
            "delta_folha_pct": float(out.delta_folha_pct),
            "delta_folha_mes": float(out.delta_folha_mes),
            "notas": {
                "tamanho": round(nota_tamanho, 1),
                "representatividade": round(nota_repr, 1),
                "impacto_medio": round(nota_impacto, 1),
                "facilidade": round(nota_facilidade, 1),
            },
            "score": round(score, 1),
            "explicacao": explicacao,
        })

    candidatas.sort(key=lambda c: c["score"], reverse=True)
    return candidatas[:top_k]


# =============================================================================
# Notas individuais (0-100)
# =============================================================================
def _nota_tamanho(cluster: str) -> float:
    """Cluster M e G são mais representativos para piloto."""
    return {"PP": 30.0, "P": 60.0, "M": 95.0, "G": 80.0}.get(cluster, 50.0)


def _nota_representatividade(brand: str, tipo: str) -> float:
    """Shopping T&F = caso mais comum (~75% da rede T&F)."""
    base = 90.0 if brand == "track_field" else 60.0
    if tipo == "shopping":
        base *= 1.0
    elif tipo == "rua":
        base *= 0.85
    else:  # outlet
        base *= 0.65
    return min(base, 100.0)


def _nota_impacto_medio(delta_pct: float, mediano: float) -> float:
    """Lojas com delta próximo da mediana extrapolam melhor (menor variância)."""
    distancia_pp = abs(delta_pct - mediano)
    # 0pp distancia → 100; 5pp → 50; 10pp+ → 0
    return max(0.0, 100.0 - distancia_pp * 10)


def _nota_facilidade(fte_total: float) -> float:
    """Lojas com 8-15 FTEs são as mais "fáceis" de pilotar.
    Pequenas (<5) têm pouca amostra; muito grandes (>25) são complexas."""
    if 8 <= fte_total <= 15:
        return 100.0
    if 5 <= fte_total < 8 or 15 < fte_total <= 20:
        return 75.0
    if fte_total < 5:
        return 30.0
    if fte_total > 25:
        return 40.0
    return 60.0


# =============================================================================
# Justificativa em linguagem natural
# =============================================================================
def _explicar(
    *,
    cluster: str,
    brand: str,
    tipo: str,
    delta_pct: float,
    delta_mediano: float,
    fte_total: float,
) -> list[str]:
    motivos: list[str] = []

    if cluster in ("M", "G"):
        motivos.append(f"Cluster {cluster} (representativo do mix da rede).")
    if brand == "track_field" and tipo == "shopping":
        motivos.append("T&F shopping (perfil mais comum: ~75% da rede).")

    distancia = abs(delta_pct - delta_mediano)
    if distancia <= 1.5:
        motivos.append(
            f"Δ folha de {delta_pct:.1f}% está colado na mediana da rede "
            f"({delta_mediano:.1f}%) — extrapolação confiável."
        )
    elif distancia <= 4:
        motivos.append(
            f"Δ folha de {delta_pct:.1f}% próximo da mediana ({delta_mediano:.1f}%)."
        )
    else:
        motivos.append(
            f"Δ folha de {delta_pct:.1f}% diverge da mediana ({delta_mediano:.1f}%) — "
            f"piloto serve como caso atípico."
        )

    if 8 <= fte_total <= 15:
        motivos.append(
            f"Headcount de {fte_total:.0f} FTEs é ideal para piloto "
            f"(amostra suficiente, complexidade baixa)."
        )
    elif fte_total < 5:
        motivos.append(f"Headcount baixo ({fte_total:.0f} FTEs) — limita conclusões.")
    elif fte_total > 25:
        motivos.append(f"Headcount alto ({fte_total:.0f} FTEs) — piloto complexo.")

    return motivos
