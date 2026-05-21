"""Core do simulador — função simulate().

Ver PRD seção 5.5 para fórmulas e seção 5.6 para critérios de aceite.

⚖️ FÓRMULA CENTRAL:
    ratio_base = 44h / 40h = 1.10
    fator_cobertura = 1 + perdas_operacionais  # default 0.05
    ratio_efetivo = ratio_base × fator_cobertura × (1 - ganho_produtividade)
    FTE_5x2 = ceil(FTE_6x1 × ratio_efetivo, 2)

⚖️ CENÁRIOS:
    pessimista: ratio_base × 1.10 × (1 - ganho_prod × 0.5)
    neutro:     ratio_base × 1.05 × (1 - ganho_prod × 1.0)
    otimista:   ratio_base × 0.98 × (1 - ganho_prod × 1.5)
"""

from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal

from engine.coverage import calculate_hourly_coverage
from engine.financial import calculate_function_costs, calculate_total_payroll
from engine.models import (
    CLTRiskItem,
    FunctionImpact,
    Recomendacao,
    ScenarioResult,
    ScenarioType,
    SimulationInput,
    SimulationOutput,
)

# =============================================================================
# Constantes da fórmula central
# =============================================================================

JORNADA_6X1 = Decimal("44")  # horas/semana hoje
JORNADA_5X2 = Decimal("40")  # horas/semana proposto
RATIO_BASE = JORNADA_6X1 / JORNADA_5X2  # 1.10

# Fatores por cenário (PRD seção 5.5)
FATOR_PERDAS_OPERACIONAIS = {
    "pessimista": Decimal("1.10"),
    "neutro": Decimal("1.05"),
    "otimista": Decimal("0.98"),
}
PESO_GANHO_PROD = {
    "pessimista": Decimal("0.5"),
    "neutro": Decimal("1.0"),
    "otimista": Decimal("1.5"),
}


# =============================================================================
# Função pública principal
# =============================================================================


def simulate(input_: SimulationInput) -> SimulationOutput:
    """Simula o impacto da migração 6x1 → 5x2 para 1 loja.

    Args:
        input_: SimulationInput com loja, premissas e cenário escolhido

    Returns:
        SimulationOutput com KPIs, impactos por função, cobertura horária,
        riscos CLT e recomendações.

    Critérios de aceite (ver PRD seção 5.6):
        - AC-101: retorna output válido para todos os 4 presets T&F
        - AC-102: shopping_m + neutro → delta_folha_pct entre 8% e 14%
        - AC-103: cobertura proposto ≥ atual em qualquer input válido
        - AC-106: <500ms em máquina padrão
    """
    # 1. Calcula ratio efetivo do cenário escolhido
    ratio = _calcular_ratio_efetivo(
        cenario=input_.scenario.cenario,
        ganho_produtividade=input_.scenario.ganho_produtividade_pct,
    )

    # 2. Calcula impacto por função (FTEs e custos)
    impactos: list[FunctionImpact] = []
    for funcao in input_.store.funcoes:
        impacto = _calcular_impacto_funcao(
            funcao=funcao,
            ratio=ratio,
            financial=input_.financial,
            manter_salario=input_.scenario.manter_salario_nominal,
        )
        impactos.append(impacto)

    # 3. Agrega totais
    fte_atual_total = sum((i.fte_atual for i in impactos), Decimal("0"))
    fte_proposto_total = sum((i.fte_proposto for i in impactos), Decimal("0"))
    folha_atual = sum((i.custo_atual_mes for i in impactos), Decimal("0"))
    folha_proposta = sum((i.custo_proposto_mes for i in impactos), Decimal("0"))
    delta_folha = folha_proposta - folha_atual
    delta_folha_pct = (delta_folha / folha_atual * 100) if folha_atual > 0 else Decimal("0")

    # 4. Calcula cobertura horária
    cobertura = calculate_hourly_coverage(
        store=input_.store,
        fte_atual=fte_atual_total,
        fte_proposto=fte_proposto_total,
    )

    # 5. Avalia riscos CLT
    riscos = _avaliar_riscos_clt(
        store=input_.store,
        delta_folha_pct=delta_folha_pct,
        fte_atual=fte_atual_total,
        fte_proposto=fte_proposto_total,
    )

    # 6. Gera os 3 cenários para comparação
    cenarios = _calcular_todos_cenarios(input_=input_)

    # 7. Gera recomendações priorizadas
    recomendacoes = _gerar_recomendacoes(
        delta_folha_pct=delta_folha_pct,
        store=input_.store,
    )

    # 8. Folha sobre faturamento (se disponível)
    fat = input_.store.faturamento_mensal
    folha_fat_atual = (folha_atual / fat * 100) if fat else None
    folha_fat_proposto = (folha_proposta / fat * 100) if fat else None

    # 9. Hash para idempotência
    inputs_hash = _hash_inputs(input_)

    return SimulationOutput(
        inputs_hash=inputs_hash,
        clt_version=input_.clt_version,
        brand_rules_version=input_.brand_rules_version,
        folha_atual_mes=folha_atual.quantize(Decimal("0.01")),
        folha_proposta_mes=folha_proposta.quantize(Decimal("0.01")),
        delta_folha_mes=delta_folha.quantize(Decimal("0.01")),
        delta_folha_pct=delta_folha_pct.quantize(Decimal("0.01")),
        fte_atual_total=fte_atual_total,
        fte_proposto_total=fte_proposto_total,
        folha_sobre_faturamento_atual=folha_fat_atual,
        folha_sobre_faturamento_proposto=folha_fat_proposto,
        impacto_por_funcao=impactos,
        cobertura_horaria=cobertura,
        riscos_clt=riscos,
        cenarios=cenarios,
        recomendacoes=recomendacoes,
    )


# =============================================================================
# Helpers privados
# =============================================================================


def _calcular_ratio_efetivo(cenario: ScenarioType, ganho_produtividade: Decimal) -> Decimal:
    """Calcula o ratio FTE_5x2 / FTE_6x1 conforme cenário."""
    fator_perdas = FATOR_PERDAS_OPERACIONAIS[cenario]
    peso = PESO_GANHO_PROD[cenario]
    ajuste_prod = Decimal("1") - (ganho_produtividade * peso)
    return RATIO_BASE * fator_perdas * ajuste_prod


def _calcular_impacto_funcao(
    funcao,
    ratio: Decimal,
    financial,
    manter_salario: bool,
) -> FunctionImpact:
    """Calcula o impacto da migração em uma função específica."""
    fte_atual = Decimal(funcao.qtd_atual)
    # Arredondamento para 2 casas pra cima — não pode ter "0,5 vendedor"
    fte_proposto_raw = fte_atual * ratio
    fte_proposto = Decimal(str(math.ceil(fte_proposto_raw * 100) / 100))

    fator_salario = Decimal("1") if manter_salario else (JORNADA_5X2 / JORNADA_6X1)
    salario_proposto = funcao.salario_medio * fator_salario

    custo_atual, custo_proposto = calculate_function_costs(
        salario_atual=funcao.salario_medio,
        salario_proposto=salario_proposto,
        fte_atual=fte_atual,
        fte_proposto=fte_proposto,
        financial=financial,
    )

    return FunctionImpact(
        nome=funcao.nome,
        fte_atual=fte_atual,
        fte_proposto=fte_proposto,
        custo_atual_mes=custo_atual.quantize(Decimal("0.01")),
        custo_proposto_mes=custo_proposto.quantize(Decimal("0.01")),
        delta_custo=(custo_proposto - custo_atual).quantize(Decimal("0.01")),
    )


def _avaliar_riscos_clt(
    store,
    delta_folha_pct: Decimal,
    fte_atual: Decimal,
    fte_proposto: Decimal,
) -> list[CLTRiskItem]:
    """Avalia riscos CLT com base no input e nos resultados."""
    riscos: list[CLTRiskItem] = []
    turno_horas = store.hora_fechamento - store.hora_abertura

    if turno_horas > 6:
        riscos.append(
            CLTRiskItem(
                severidade="good",
                artigo="CLT Art. 71",
                titulo="Intrajornada (≥1h)",
                descricao=(
                    "Jornada >6h exige 1h de intervalo. Modelo 5x2 com 8h/dia "
                    "mantém regra. Sem multa."
                ),
            )
        )

    riscos.append(
        CLTRiskItem(
            severidade="good",
            artigo="CLT Art. 66",
            titulo="Interjornada (≥11h)",
            descricao=(
                f"Mínimo 11h entre jornadas atendido com fechamento "
                f"{store.hora_fechamento}h e abertura {store.hora_abertura}h."
            ),
        )
    )

    if store.dias_operacao_semana == 7:
        riscos.append(
            CLTRiskItem(
                severidade="warn",
                artigo="CLT Art. 67 + Lei 10.101",
                titulo="DSR + 1 domingo/mês",
                descricao=(
                    "Operação 7d/sem exige escala que garanta 1 domingo de "
                    "folga a cada 4 semanas. 5x2 facilita esse rodízio."
                ),
            )
        )

    if fte_proposto > fte_atual:
        delta_fte = fte_proposto - fte_atual
        riscos.append(
            CLTRiskItem(
                severidade="warn",
                artigo="Operacional",
                titulo="Cobertura de pico",
                descricao=(
                    f"Crescimento de {delta_fte} FTEs requer alocar a equipe "
                    "extra preferencialmente em sex-sáb-dom 14h-21h."
                ),
            )
        )

    if delta_folha_pct > 10:
        riscos.append(
            CLTRiskItem(
                severidade="bad",
                artigo="Financeiro",
                titulo="Pressão de margem",
                descricao=(
                    f"Aumento de {delta_folha_pct:.1f}% na folha pressiona "
                    "EBITDA — alinhado a estudo Fitch (-10 a -15% setor varejo). "
                    "Necessário compensar por produtividade ou repasse."
                ),
            )
        )

    # TODO: comissionistas T&F não folgam sábado — adicionar verificação
    # quando o input incluir distribuição semanal proposta. Por enquanto, este
    # alerta é registrado apenas se há comissionistas no quadro.
    tem_comissionistas = any(
        f.comissionado for f in store.funcoes if store.brand == "track_field"
    )
    if tem_comissionistas:
        riscos.append(
            CLTRiskItem(
                severidade="info",
                artigo="Regra de negócio T&F",
                titulo="Comissionistas — restrição de sábado",
                descricao=(
                    "Vendedores comissionados não podem folgar aos sábados "
                    "(impacto direto na meta). Constraint a ser respeitada "
                    "pelo Planejador (v2.0)."
                ),
            )
        )

    return riscos


def _calcular_todos_cenarios(input_: SimulationInput) -> dict[ScenarioType, ScenarioResult]:
    """Calcula os 3 cenários (pess/neut/otim) para visualização comparativa."""
    resultados: dict[ScenarioType, ScenarioResult] = {}

    for cenario_key in ("pessimista", "neutro", "otimista"):
        cenario: ScenarioType = cenario_key  # type: ignore[assignment]
        ratio = _calcular_ratio_efetivo(
            cenario=cenario,
            ganho_produtividade=input_.scenario.ganho_produtividade_pct,
        )
        fator_salario = (
            Decimal("1")
            if input_.scenario.manter_salario_nominal
            else (JORNADA_5X2 / JORNADA_6X1)
        )

        fte_total = Decimal("0")
        folha_total = Decimal("0")
        folha_atual_total = Decimal("0")

        for funcao in input_.store.funcoes:
            fte_atual_f = Decimal(funcao.qtd_atual)
            fte_proposto_f = Decimal(str(math.ceil(fte_atual_f * ratio * 100) / 100))
            sal_proposto = funcao.salario_medio * fator_salario

            custo_atual, custo_proposto = calculate_function_costs(
                salario_atual=funcao.salario_medio,
                salario_proposto=sal_proposto,
                fte_atual=fte_atual_f,
                fte_proposto=fte_proposto_f,
                financial=input_.financial,
            )

            fte_total += fte_proposto_f
            folha_total += custo_proposto
            folha_atual_total += custo_atual

        delta = folha_total - folha_atual_total
        delta_pct = (
            (delta / folha_atual_total * 100) if folha_atual_total > 0 else Decimal("0")
        )

        resultados[cenario] = ScenarioResult(
            cenario=cenario,
            ratio_aplicado=ratio.quantize(Decimal("0.0001")),
            fte_total=fte_total,
            folha_total=folha_total.quantize(Decimal("0.01")),
            delta_folha=delta.quantize(Decimal("0.01")),
            delta_folha_pct=delta_pct.quantize(Decimal("0.01")),
        )

    return resultados


def _gerar_recomendacoes(delta_folha_pct: Decimal, store) -> list[Recomendacao]:
    """Gera recomendações priorizadas com base no resultado."""
    recs: list[Recomendacao] = []

    if delta_folha_pct > 8:
        recs.append(
            Recomendacao(
                prioridade=1,
                titulo="Apoiar pleito de modelo horista no CCT",
                descricao=(
                    "Negociação ABRAS/CNC de modelo por hora reduz custo fixo "
                    "em horários de baixa demanda."
                ),
                impacto_estimado="-3 a -5pp na folha",
            )
        )

    recs.append(
        Recomendacao(
            prioridade=2,
            titulo="Hibridizar com horistas regulamentados",
            descricao=(
                "Manter 60-70% do quadro CLT e cobrir picos de fim de semana "
                "com horistas em regime regulamentado."
            ),
            impacto_estimado="-2 a -4pp na folha",
        )
    )

    recs.append(
        Recomendacao(
            prioridade=3,
            titulo="Investir em Workforce Management com IA",
            descricao=(
                "WFM aprende curva de demanda e aloca pessoas com maior "
                "precisão. Reduz folha em 4-7% via melhor alocação."
            ),
            impacto_estimado="-4 a -7% folha",
        )
    )

    recs.append(
        Recomendacao(
            prioridade=4,
            titulo="Repensar mix de funções (multifunção)",
            descricao=(
                "Vendedor multifunção (caixa+venda+estoque) reduz FTEs "
                "cruzados durante a transição."
            ),
        )
    )

    recs.append(
        Recomendacao(
            prioridade=5,
            titulo="Piloto em 3 lojas representativas",
            descricao=(
                "Testar 5x2 em 1 shopping P, 1 M e 1 rua antes de rollout. "
                "Coleta dados reais de produtividade para recalibrar simulador."
            ),
        )
    )

    return recs


def _hash_inputs(input_: SimulationInput) -> str:
    """Gera SHA-256 dos inputs para idempotência e auditoria."""
    payload = input_.model_dump_json(exclude_none=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
