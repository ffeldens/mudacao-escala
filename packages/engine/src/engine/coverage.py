"""Cálculo da curva de cobertura horária.

Para cada hora do dia em que a loja está aberta:
- Calcula FTEs disponíveis em escala atual (6x1)
- Calcula FTEs disponíveis em escala proposta (5x2)
- Estima a demanda como proxy a partir de ticket_history (se disponível)
  ou de uma curva default por tipo de varejo de moda

Quando `store.ticket_history` está populado, a demanda_proxy é derivada da
média horária do histórico (agregando todos os dias da semana operados).
Caso contrário, usa curvas default por marca (varejo de moda vs café).
"""

from __future__ import annotations

from decimal import Decimal

from engine.models import CoverageHourPoint, StoreInput


def calculate_hourly_coverage(
    store: StoreInput,
    fte_atual: Decimal,
    fte_proposto: Decimal,
) -> list[CoverageHourPoint]:
    """Gera curva de cobertura horária para a loja.

    Args:
        store: dados da loja
        fte_atual: total de FTEs em 6x1
        fte_proposto: total de FTEs em 5x2

    Returns:
        Lista de CoverageHourPoint, uma entrada por hora aberta.
    """
    pontos: list[CoverageHourPoint] = []
    media_por_hora = _media_por_hora_do_historico(store) if store.ticket_history else None

    # Para normalizar a demanda em "FTEs equivalentes", precisamos de uma
    # referência de capacidade. Usamos: 1 FTE atende ~12 tickets/hora numa loja
    # operando em ritmo normal (aproximação, parametrizar no futuro).
    tickets_por_fte_hora = Decimal("12")

    for hora in range(store.hora_abertura, store.hora_fechamento):
        cobertura_factor_6x1 = _cobertura_factor_6x1(hora)
        cobertura_factor_5x2 = _cobertura_factor_5x2(hora)

        if media_por_hora is not None and hora in media_por_hora:
            # Demanda derivada do histórico real/sintético
            demanda_proxy = (media_por_hora[hora] / tickets_por_fte_hora).quantize(
                Decimal("0.01")
            )
        else:
            # Fallback: curva default por marca
            demanda_factor = _demanda_factor_default(hora, store.brand)
            demanda_proxy = (fte_atual * demanda_factor * Decimal("0.55")).quantize(
                Decimal("0.01")
            )

        ponto = CoverageHourPoint(
            hora=hora,
            fte_atual=(fte_atual * cobertura_factor_6x1).quantize(Decimal("0.01")),
            fte_proposto=(fte_proposto * cobertura_factor_5x2).quantize(Decimal("0.01")),
            demanda_proxy=demanda_proxy,
        )
        pontos.append(ponto)

    return pontos


def _media_por_hora_do_historico(store: StoreInput) -> dict[int, Decimal]:
    """Agrega o ticket_history em média de tickets por hora (todos os DOWs).

    Returns:
        dict {hora: media_tickets} — média ponderada simples sobre os pontos
        históricos disponíveis para aquela hora.
    """
    grupos: dict[int, list[Decimal]] = {}
    for ponto in store.ticket_history:
        grupos.setdefault(ponto.hora, []).append(ponto.media_tickets)

    return {
        hora: (sum(valores) / Decimal(len(valores)))
        for hora, valores in grupos.items()
    }


def _demanda_factor_default(hora: int, brand: str) -> Decimal:
    """Curva default de demanda por hora — fallback quando não há histórico.

    T&F (varejo): pico 14h-21h
    TFC (café):   pico café-da-manhã + almoço + final de tarde
    """
    if brand == "tfc":
        if 7 <= hora <= 9:
            return Decimal("0.85")
        if 12 <= hora <= 14:
            return Decimal("0.95")
        if 17 <= hora <= 19:
            return Decimal("0.80")
        return Decimal("0.45")

    if 14 <= hora <= 21:
        return Decimal("0.95")
    if 12 <= hora <= 13:
        return Decimal("0.70")
    if hora < 11:
        return Decimal("0.45")
    return Decimal("0.60")


def _cobertura_factor_6x1(hora: int) -> Decimal:
    """Distribuição típica da equipe ao longo do dia em 6x1."""
    if 14 <= hora <= 21:
        return Decimal("0.85")
    if 12 <= hora <= 13:
        return Decimal("0.60")
    if hora < 11:
        return Decimal("0.40")
    return Decimal("0.65")


def _cobertura_factor_5x2(hora: int) -> Decimal:
    """Distribuição típica da equipe ao longo do dia em 5x2 (mais cobertura em pico)."""
    if 14 <= hora <= 21:
        return Decimal("0.92")
    if 12 <= hora <= 13:
        return Decimal("0.65")
    if hora < 11:
        return Decimal("0.42")
    return Decimal("0.70")
