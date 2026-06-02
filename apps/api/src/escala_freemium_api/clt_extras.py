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

from escala_freemium_api.clt_scheduler import build_schedule_from_horarios
from escala_freemium_api.horarios import (
    dias_operacao_efetivos,
    get_horario_dia,
    horas_semanais_operacao,
)
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
    # Horas/semana levando em conta horários diferenciados (seg-sex/sab/dom)
    horas_semanais_necessarias = horas_semanais_operacao(req)
    dias_op_efetivos = dias_operacao_efetivos(req)
    horas_dia_seg_sex = req.hora_fechamento - req.hora_abertura

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
                    f"Sua operação roda {dias_op_efetivos} dias/semana, "
                    f"totalizando {horas_semanais_necessarias}h/semana. "
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
    if dias_op_efetivos == 7 and req.fte_atual < 2:
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
    horas_dia = horas_dia_seg_sex  # dia mais longo (seg-sex)
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
    # Avalia AS DUAS grades (atual 6x1 + proposto 5x2) — gera risk separado
    # pra cada uma porque o user pode estar vendo vermelhos em qualquer das duas.
    # =========================================================================
    horarios = {d: get_horario_dia(req, d) for d in range(7)}

    sched_atual = build_schedule_from_horarios(
        fte_count=float(req.fte_atual),
        arredondamento_mode=req.arredondamento_fte,
        horarios_por_dia=horarios,
        modelo="6x1",
    )
    sched_prop = build_schedule_from_horarios(
        fte_count=float(result.fte_proposto),
        arredondamento_mode=req.arredondamento_fte,
        horarios_por_dia=horarios,
        modelo="5x2",
    )

    def _risk_gap(
        sched: object, modelo_label: str, jornada: str
    ) -> dict[str, Any] | None:
        if sched.slots_descobertos == 0 or sched.slots_total == 0:
            return None
        pct = sched.slots_descobertos / sched.slots_total * 100
        # Qualquer slot sem ninguém na loja aberta é violação operacional
        # grave — não tem como funcionar com 0 pessoas. Sempre 'bad'.
        # Severidade poderia escalar conforme volume, mas mesmo 1 slot
        # já é problema sério que precisa virar atenção do gestor.
        return {
            "severidade": "bad",
            "artigo": f"Cobertura simulada ({modelo_label})",
            "titulo": (
                f"{sched.slots_descobertos} "
                f"{'slot' if sched.slots_descobertos == 1 else 'slots'} "
                f"sem nenhum FTE na grade do {modelo_label}"
            ),
            "descricao": (
                f"Distribuindo {sched.fte_full_count} FTE(s) full + "
                f"{sched.fte_meio_count} meio-turno(s) com shifts reais "
                f"({jornada}), sobra(m) {sched.slots_descobertos}h/semana "
                f"sem ninguém na loja ({pct:.1f}% do tempo de operação). "
                f"Veja a grade do {modelo_label} no relatório — células em "
                f"vermelho são esses gaps. "
                f"⚠️ Mesmo 1 hora sem cobertura é violação operacional — "
                f"a loja está aberta sem ninguém pra atender. Isso pode "
                f"acontecer mesmo com cobertura agregada OK por causa da "
                f"alocação heurística (2 patterns manhã/tarde) deixar "
                f"horários extremos ou de transição descobertos. Numa "
                f"escala REAL otimizada (Planejador Pro), esses gaps "
                f"desaparecem."
            ),
        }

    if (r := _risk_gap(sched_atual, "modelo atual 6x1", "8h + 1h intervalo")):
        risks.append(r)
    if (r := _risk_gap(sched_prop, "modelo proposto 5x2", "8h + 1h intervalo + meio-turno")):
        risks.append(r)

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
