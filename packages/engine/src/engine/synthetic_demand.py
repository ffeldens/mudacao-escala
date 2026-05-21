"""Gerador de histórico sintético de tickets para alimentar simulações sem dados reais.

Sem depender de input do cliente, gera curvas de demanda plausíveis por marca:
- T&F (varejo moda): pico tarde-noite forte, sex/sáb mais movimentado
- TFC (café): 3 picos (manhã, almoço, tarde), domingo mais leve

A curva produzida é determinística (semente baseada em store.codigo) para garantir
idempotência — mesma loja → mesmo histórico sintético.
"""

from __future__ import annotations

import hashlib
import math
import random
from decimal import Decimal

from engine.models import Brand, TicketHistoryPoint


# =============================================================================
# Multiplicadores típicos por dia da semana (varejo brasileiro)
# 0 = segunda, 6 = domingo
# =============================================================================
_DOW_T_F = {0: 0.85, 1: 0.85, 2: 0.95, 3: 1.00, 4: 1.20, 5: 1.45, 6: 1.10}
_DOW_TFC = {0: 0.95, 1: 1.00, 2: 1.00, 3: 1.05, 4: 1.20, 5: 1.30, 6: 0.85}


def generate_ticket_history(
    *,
    brand: Brand,
    hora_abertura: int,
    hora_fechamento: int,
    dias_operacao_semana: int = 7,
    cluster_size_factor: Decimal = Decimal("1.0"),
    semente: str = "default",
    ruido_pct: Decimal = Decimal("0.10"),
) -> list[TicketHistoryPoint]:
    """Gera histórico sintético de tickets por (dia_semana × hora).

    Args:
        brand: track_field ou tfc (define forma da curva).
        hora_abertura: 0-23.
        hora_fechamento: 1-24.
        dias_operacao_semana: 1-7 (limita os DOWs gerados).
        cluster_size_factor: escala vertical da demanda (PP=0.5, P=0.8, M=1.0, G=1.5).
        semente: string para tornar a geração determinística por loja.
        ruido_pct: amplitude relativa do ruído gaussiano (0-1).

    Returns:
        Lista de TicketHistoryPoint (um por hora-aberta × DOW operado).
    """
    rng = random.Random(_seed_from_string(semente))
    dow_weights = _DOW_TFC if brand == "tfc" else _DOW_T_F
    dows_operados = list(range(min(dias_operacao_semana, 7)))

    pontos: list[TicketHistoryPoint] = []
    for dow in dows_operados:
        weight_dow = Decimal(str(dow_weights.get(dow, 1.0)))
        for hora in range(hora_abertura, hora_fechamento):
            base = _curva_horaria_base(brand, hora)
            media = (
                base
                * weight_dow
                * cluster_size_factor
                * Decimal(str(1 + (rng.random() - 0.5) * 2 * float(ruido_pct)))
            )
            desvio = media * Decimal("0.18")  # CV típico de 18% no varejo
            pontos.append(
                TicketHistoryPoint(
                    dia_semana=dow,
                    hora=hora,
                    media_tickets=media.quantize(Decimal("0.01")),
                    desvio_padrao=desvio.quantize(Decimal("0.01")),
                )
            )
    return pontos


def _curva_horaria_base(brand: Brand, hora: int) -> Decimal:
    """Curva base de tickets/hora (sem ajuste de DOW ou cluster).

    Valores em escala de "tickets típicos por hora numa loja de tamanho médio".
    """
    if brand == "tfc":
        return _curva_tfc(hora)
    return _curva_track_field(hora)


def _curva_track_field(hora: int) -> Decimal:
    """Varejo de moda esportiva: pico tarde-noite (14h-21h)."""
    # Função suave centrada em 17h com pico ~ 35 tickets/h
    pico = 17.0
    largura = 5.5
    altura = 35.0
    base = 4.0
    valor = base + altura * math.exp(-((hora - pico) ** 2) / (2 * largura**2))
    return Decimal(str(round(valor, 2)))


def _curva_tfc(hora: int) -> Decimal:
    """Café TFC: 3 picos (8h, 12h, 18h)."""
    base = 3.0
    pico_manha = 18.0 * math.exp(-((hora - 8) ** 2) / (2 * 1.8**2))
    pico_almoco = 28.0 * math.exp(-((hora - 12.5) ** 2) / (2 * 1.5**2))
    pico_tarde = 16.0 * math.exp(-((hora - 18) ** 2) / (2 * 2.0**2))
    valor = base + pico_manha + pico_almoco + pico_tarde
    return Decimal(str(round(valor, 2)))


def _seed_from_string(s: str) -> int:
    """Converte string em semente int de 32 bits para o Random."""
    return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16)


# =============================================================================
# Cluster size factors (multiplicador de escala por cluster)
# =============================================================================
CLUSTER_FACTORS: dict[str, Decimal] = {
    "PP": Decimal("0.50"),
    "P": Decimal("0.80"),
    "M": Decimal("1.00"),
    "G": Decimal("1.60"),
}
