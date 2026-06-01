"""Adapter: converte payload simplificado da API → SimulationInput do engine.

Mantém a complexidade do engine isolada do frontend. O frontend manda apenas o
necessário (FTE agregado, salário médio, porte); este módulo expande pra forma
completa que o engine espera (1 função "Equipe" agregando tudo).
"""

from __future__ import annotations

from decimal import Decimal

from engine.core import simulate as engine_simulate
from engine.models import (
    FinancialAssumptions,
    FunctionRole,
    ScenarioConfig,
    SimulationInput,
    SimulationOutput,
    StoreInput,
)

from escala_freemium_api.schemas import (
    CenarioOut,
    SetorType,
    SimulateRequest,
    SimulateResponse,
)

# Mapeamento porte → cluster do engine
_PORTE_TO_CLUSTER = {"PP": "PP", "P": "P", "M": "M", "G": "G"}

# Margem de economia potencial via WFM (Workforce Management) com IA — PRD §6.3
# Faixa: 4-7% da folha proposta. Usamos 5% como ponto médio conservador.
WFM_ECONOMY_PCT = Decimal("0.05")


def run_simulation(
    req: SimulateRequest,
    custom_financial: FinancialAssumptions | None = None,
) -> SimulateResponse:
    """Roda o engine `simulate()` e empacota a resposta simplificada.

    Args:
        req: payload da API
        custom_financial: se fornecido, substitui defaults do engine
            (encargos, VR, VT, dias úteis). Usado pra premissas
            customizadas de user logado.
    """
    # Constrói input completo pro engine
    engine_input = _build_engine_input(req, custom_financial=custom_financial)

    # Roda engine
    output: SimulationOutput = engine_simulate(engine_input)

    # Extrapolação rede: multiplica delta por N lojas
    n_lojas = req.n_lojas_rede
    delta_mes_rede = output.delta_folha_mes * n_lojas
    delta_ano_rede = delta_mes_rede * 12

    # Headline
    if output.delta_folha_mes > 0:
        headline = _format_headline_gasto(delta_mes_rede, n_lojas)
    else:
        headline = "Sua rede pode operar 5x2 sem aumento de folha (cenário raro)."

    # (helper definido abaixo)

    # Economia potencial WFM = 5% da folha proposta × N lojas
    economia_wfm = (output.folha_proposta_mes * WFM_ECONOMY_PCT * n_lojas).quantize(
        Decimal("0.01")
    )

    return SimulateResponse(
        inputs_hash=output.inputs_hash,
        folha_atual_mes=output.folha_atual_mes,
        folha_proposta_mes=output.folha_proposta_mes,
        delta_folha_mes=output.delta_folha_mes,
        delta_folha_pct=output.delta_folha_pct,
        fte_atual=output.fte_atual_total,
        fte_proposto=output.fte_proposto_total,
        fte_extras_necessarios=(output.fte_proposto_total - output.fte_atual_total).quantize(
            Decimal("0.01")
        ),
        cenarios={
            k: CenarioOut(
                cenario=v.cenario,
                ratio_aplicado=v.ratio_aplicado,
                fte_total=v.fte_total,
                folha_total=v.folha_total,
                delta_folha=v.delta_folha,
                delta_folha_pct=v.delta_folha_pct,
            )
            for k, v in output.cenarios.items()
        },
        n_lojas=n_lojas,
        delta_folha_rede_mes=delta_mes_rede.quantize(Decimal("0.01")),
        delta_folha_rede_ano=delta_ano_rede.quantize(Decimal("0.01")),
        headline=headline,
        economia_potencial_wfm=economia_wfm,
        economia_potencial_wfm_pct=(WFM_ECONOMY_PCT * 100).quantize(Decimal("0.01")),
    )


# =============================================================================
# Helpers privados
# =============================================================================


def _build_engine_input(
    req: SimulateRequest,
    custom_financial: FinancialAssumptions | None = None,
) -> SimulationInput:
    """Expande payload simplificado pra SimulationInput completo."""
    # 1 função "Equipe" agregando todos os FTEs.
    # Quando o frontend evoluir pra granular (vendedor/caixa/estoque), aqui
    # vira um loop sobre req.funcoes.
    funcoes = [
        FunctionRole(
            nome="Equipe",
            qtd_atual=req.fte_atual,
            salario_medio=req.salario_medio,
            comissionado=False,
            presenca_minima_simultanea=1,
        )
    ]

    store = StoreInput(
        codigo="freemium-001",
        nome=req.nome_loja or "Minha loja",
        brand=_setor_to_brand(req.setor),
        tipo="rua",  # default seguro pro free; user não precisa escolher
        cluster=_PORTE_TO_CLUSTER[req.porte],
        hora_abertura=req.hora_abertura,
        hora_fechamento=req.hora_fechamento,
        dias_operacao_semana=req.dias_operacao_semana,
        funcoes=funcoes,
        faturamento_mensal=req.faturamento_mensal,
    )

    scenario = ScenarioConfig(
        cenario=req.cenario,
        ganho_produtividade_pct=req.ganho_produtividade_pct,
        manter_salario_nominal=req.manter_salario_nominal,
    )

    financial = custom_financial or FinancialAssumptions()

    return SimulationInput(
        store=store,
        scenario=scenario,
        financial=financial,
    )


def _setor_to_brand(setor: SetorType) -> str:
    """Engine usa `brand` literal — mapeamos setor genérico pro mais próximo."""
    # No futuro, o engine vai ter brand="generic_retail" e "food_service".
    # Por ora, todos caem em "tfc" (regras mais permissivas que T&F).
    return "tfc"


def _format_headline_gasto(delta_mes_rede: Decimal, n_lojas: int) -> str:
    """Formata o headline mostrando o gasto extra mensal da rede."""
    valor_brl = (
        f"R$ {float(delta_mes_rede):,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )
    if n_lojas == 1:
        return f"Sua loja vai gastar {valor_brl} a mais por mês com a escala 5x2."
    return (
        f"Sua rede de {n_lojas} lojas vai gastar {valor_brl} a mais por mês "
        f"com a escala 5x2."
    )
