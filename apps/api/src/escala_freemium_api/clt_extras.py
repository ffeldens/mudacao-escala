"""Validações CLT extras — não cobertas pelo engine base.

O engine avalia artigos 71/66/67 e flags de regra de negócio, mas não
verifica viabilidade matemática do quadro (FTEs × jornada vs horas
necessárias por semana). Esses checks rodam DEPOIS do engine e enriquecem
a lista de riscos.

Usado por POST /api/me/validate-clt antes de gerar o PDF.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from escala_freemium_api.clt_scheduler import build_schedule_for_pdf
from escala_freemium_api.schemas import SimulateRequest, SimulateResponse


def evaluate_extra_risks(
    req: SimulateRequest,
    result: SimulateResponse,
) -> list[dict[str, Any]]:
    """Roda checks extras que o engine base não cobre.

    Retorna lista de risk dicts (mesma estrutura do engine: severidade,
    artigo, titulo, descricao) prontos pra serem mesclados com os do engine.
    """
    risks: list[dict[str, Any]] = []

    # =========================================================================
    # 1. Viabilidade matemática do quadro
    # =========================================================================
    horas_dia = req.hora_fechamento - req.hora_abertura
    horas_semanais_necessarias = req.dias_operacao_semana * horas_dia

    # Atual (6x1: 44h/semana por FTE)
    horas_disponiveis_atual = req.fte_atual * 44
    cobertura_atual = (
        horas_disponiveis_atual / horas_semanais_necessarias
        if horas_semanais_necessarias > 0
        else 1.0
    )

    # Proposto (5x2: 40h/semana por FTE) — usa fte_proposto do resultado
    fte_proposto = float(result.fte_proposto)
    horas_disponiveis_proposto = fte_proposto * 40
    cobertura_proposto = (
        horas_disponiveis_proposto / horas_semanais_necessarias
        if horas_semanais_necessarias > 0
        else 1.0
    )

    # ---- Risco 1A: quadro ATUAL insuficiente ----
    if cobertura_atual < 0.95:
        risks.append(
            {
                "severidade": "bad",
                "artigo": "Viabilidade operacional",
                "titulo": "Quadro atual já é insuficiente",
                "descricao": (
                    f"Sua operação roda {req.dias_operacao_semana} dias × "
                    f"{horas_dia}h = {horas_semanais_necessarias}h/semana. "
                    f"Com {req.fte_atual} FTE(s) × 44h, você tem apenas "
                    f"{horas_disponiveis_atual}h disponíveis "
                    f"({cobertura_atual * 100:.0f}% do necessário). "
                    f"Mesmo no modelo atual 6x1 isso é matematicamente "
                    f"inviável sem horas extras sistemáticas — provável "
                    f"violação de artigos da CLT já hoje."
                ),
            }
        )
    elif cobertura_atual < 1.10:
        risks.append(
            {
                "severidade": "warn",
                "artigo": "Cobertura mínima",
                "titulo": "Quadro atual sem margem de absenteísmo",
                "descricao": (
                    f"Sua cobertura atual está em "
                    f"{cobertura_atual * 100:.0f}% — só dá pra operar se "
                    f"ninguém faltar. Recomendação: manter pelo menos 110% "
                    f"de cobertura pra absorver férias, atestados e folgas."
                ),
            }
        )

    # ---- Risco 1B: quadro PROPOSTO (5x2) ainda insuficiente ----
    if cobertura_proposto < 0.95:
        deficit = horas_semanais_necessarias - horas_disponiveis_proposto
        ftes_faltam = deficit / 40
        risks.append(
            {
                "severidade": "bad",
                "artigo": "Viabilidade — pós-PEC",
                "titulo": "Modelo 5x2 proposto não cobre a operação",
                "descricao": (
                    f"Com {fte_proposto:.1f} FTE(s) × 40h = "
                    f"{horas_disponiveis_proposto:.0f}h disponíveis, "
                    f"cobre {cobertura_proposto * 100:.0f}% das "
                    f"{horas_semanais_necessarias}h necessárias. "
                    f"Faltam ~{ftes_faltam:.1f} FTE(s) adicionais pra "
                    f"viabilizar a operação no modelo 5x2."
                ),
            }
        )
    elif cobertura_proposto < 1.10:
        risks.append(
            {
                "severidade": "warn",
                "artigo": "Cobertura mínima — pós-PEC",
                "titulo": "Quadro 5x2 sem margem de absenteísmo",
                "descricao": (
                    f"Cobertura proposta: {cobertura_proposto * 100:.0f}%. "
                    f"Considere contratar 1-2 FTEs adicionais pra absorver "
                    f"absenteísmo, férias e atestados sem comprometer a "
                    f"operação."
                ),
            }
        )

    # =========================================================================
    # 2. Operação 7d/semana com poucos FTEs (DSR)
    # =========================================================================
    if req.dias_operacao_semana == 7 and req.fte_atual < 2:
        risks.append(
            {
                "severidade": "bad",
                "artigo": "CLT Art. 67 (DSR)",
                "titulo": "DSR impossível com menos de 2 FTEs",
                "descricao": (
                    "Operação 7 dias/semana exige rotatividade de folgas. "
                    "Com apenas 1 FTE não há como garantir o Descanso "
                    "Semanal Remunerado (DSR) sem fechar a loja. Mínimo "
                    "operacional: 2 FTEs em revezamento."
                ),
            }
        )

    # =========================================================================
    # 3. Jornada diária excessiva
    # =========================================================================
    # CLT Art 59: jornada máxima 10h/dia (8h + 2h extras). Se a operação
    # exige mais que isso por dia e o headcount não permite turnos, alerta.
    if horas_dia > 10 and req.fte_atual <= 2:
        risks.append(
            {
                "severidade": "bad",
                "artigo": "CLT Art. 59",
                "titulo": "Jornada diária excessiva",
                "descricao": (
                    f"Operação de {horas_dia}h/dia exige rodízio de turnos. "
                    f"Com {req.fte_atual} FTE(s), o(s) trabalhador(es) "
                    f"seria(m) submetido(s) a jornada acima do limite legal "
                    f"de 10h/dia (8h regulares + 2h extras). "
                    f"Necessário aumentar o quadro pra trabalhar em turnos."
                ),
            }
        )
    elif horas_dia > 10 and req.fte_atual <= 3:
        risks.append(
            {
                "severidade": "warn",
                "artigo": "CLT Art. 59 + Turnos",
                "titulo": "Jornada longa exige turnos bem estruturados",
                "descricao": (
                    f"Operação de {horas_dia}h/dia com apenas "
                    f"{req.fte_atual} FTEs requer turnos rotativos rígidos. "
                    f"Cuidado com interjornada (mín 11h) e DSR."
                ),
            }
        )

    # =========================================================================
    # 3.5. Slots descobertos pela alocação real de shifts (Validador 2.0)
    # =========================================================================
    sched_prop = build_schedule_for_pdf(
        fte_count=float(result.fte_proposto),
        arredondamento_mode=req.arredondamento_fte,
        dias_operacao=req.dias_operacao_semana,
        hora_abertura=req.hora_abertura,
        hora_fechamento=req.hora_fechamento,
        modelo="5x2",
    )

    if sched_prop.slots_descobertos > 0 and sched_prop.slots_total > 0:
        pct_descoberto = (
            sched_prop.slots_descobertos / sched_prop.slots_total * 100
        )
        severidade = "bad" if pct_descoberto > 10 else "warn"
        risks.append(
            {
                "severidade": severidade,
                "artigo": "Cobertura simulada (Validador 2.0)",
                "titulo": (
                    f"{sched_prop.slots_descobertos} slots sem nenhum FTE "
                    f"na semana modelo (5x2)"
                ),
                "descricao": (
                    f"Distribuindo {sched_prop.fte_full_count} FTE(s) full e "
                    f"{sched_prop.fte_meio_count} meio-turno(s) com shifts "
                    f"reais (8h + 1h intervalo), sobram "
                    f"{sched_prop.slots_descobertos}h/semana sem ninguém na "
                    f"loja ({pct_descoberto:.0f}% do tempo de operação). "
                    f"Veja a grade no relatório — slots em vermelho. "
                    f"Solução: aumentar o quadro OU usar Planejador Pro pra "
                    f"otimizar a distribuição."
                ),
            }
        )

    # =========================================================================
    # 4. Operação noturna sem adicional
    # =========================================================================
    if req.hora_fechamento >= 22:
        horas_noturnas = min(5, req.hora_fechamento - 22)  # 22h-5h é noturno
        risks.append(
            {
                "severidade": "info",
                "artigo": "CLT Art. 73",
                "titulo": "Horário noturno requer adicional 20%",
                "descricao": (
                    f"Fechamento às {req.hora_fechamento}h cai em horário "
                    f"noturno ({horas_noturnas}h após 22h). Horas trabalhadas "
                    f"nesse período exigem adicional noturno de 20% sobre o "
                    f"salário. Verifique se a folha proposta considera isso."
                ),
            }
        )

    return risks


def merge_risks(
    engine_risks: list[dict[str, Any]],
    extra_risks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Mescla riscos do engine + extras, ordenando por severidade.

    Ordem: bad → warn → info → good (mais críticos primeiro no PDF).
    """
    severity_order = {"bad": 0, "warn": 1, "info": 2, "good": 3}
    all_risks = engine_risks + extra_risks
    return sorted(
        all_risks,
        key=lambda r: severity_order.get(r.get("severidade", "info"), 99),
    )
