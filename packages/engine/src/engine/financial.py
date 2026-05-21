"""Cálculo de custo financeiro por função.

Componentes do custo mensal:
    custo_unitario = salario × (1 + encargos_pct) + benefícios_mensais
    benefícios_mensais = (vr_dia + vt_dia) × dias_uteis_mes
    custo_total = custo_unitario × FTE
"""

from __future__ import annotations

from decimal import Decimal

from engine.models import FinancialAssumptions


def calculate_function_costs(
    salario_atual: Decimal,
    salario_proposto: Decimal,
    fte_atual: Decimal,
    fte_proposto: Decimal,
    financial: FinancialAssumptions,
) -> tuple[Decimal, Decimal]:
    """Calcula custo total mensal de uma função (atual e proposto).

    Returns:
        Tupla (custo_atual_mes, custo_proposto_mes)
    """
    beneficios_mes = (financial.vr_dia + financial.vt_dia) * Decimal(financial.dias_uteis_mes)

    custo_unit_atual = salario_atual * (Decimal("1") + financial.encargos_pct) + beneficios_mes
    custo_unit_proposto = (
        salario_proposto * (Decimal("1") + financial.encargos_pct) + beneficios_mes
    )

    return (
        fte_atual * custo_unit_atual,
        fte_proposto * custo_unit_proposto,
    )


def calculate_total_payroll(
    funcoes_custos: list[tuple[Decimal, Decimal]],
) -> tuple[Decimal, Decimal]:
    """Soma totais de folha (atual e proposto) a partir de custos por função."""
    total_atual = sum((c[0] for c in funcoes_custos), Decimal("0"))
    total_proposto = sum((c[1] for c in funcoes_custos), Decimal("0"))
    return total_atual, total_proposto
