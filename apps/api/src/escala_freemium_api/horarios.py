"""Helpers pra trabalhar com horários de funcionamento por tipo de dia.

Modelo: 3 perfis (seg-sex / sáb / dom). Sábado e domingo podem:
- Herdar o horário dos dias úteis (None nos campos)
- Ter horário próprio (campos preenchidos)
- Ficar fechados (toggle `*_fechado=True`)

Não suportamos horário individual por dia da semana — se cobre 99% do varejo
sem isso, manter a UI simples vale mais.
"""

from __future__ import annotations

from escala_freemium_api.schemas import SimulateRequest


def get_horario_dia(
    req: SimulateRequest, dia: int
) -> tuple[int, int] | None:
    """Retorna (abertura, fechamento) do dia ou None se fechado.

    Args:
        req: payload da simulação
        dia: 0=segunda ... 6=domingo

    Returns:
        Tupla (abertura, fechamento) ou None se loja fechada nesse dia
    """
    if 0 <= dia <= 4:  # seg-sex
        return (req.hora_abertura, req.hora_fechamento)

    if dia == 5:  # sábado
        if req.sabado_fechado:
            return None
        ab = req.hora_abertura_sabado
        fc = req.hora_fechamento_sabado
        return (
            ab if ab is not None else req.hora_abertura,
            fc if fc is not None else req.hora_fechamento,
        )

    if dia == 6:  # domingo
        if req.domingo_fechado:
            return None
        ab = req.hora_abertura_domingo
        fc = req.hora_fechamento_domingo
        return (
            ab if ab is not None else req.hora_abertura,
            fc if fc is not None else req.hora_fechamento,
        )

    return None


def dias_operacao_efetivos(req: SimulateRequest) -> int:
    """Quantos dias da semana a loja efetivamente abre.

    Calcula a partir dos toggles `sabado_fechado` / `domingo_fechado`
    OU honra `dias_operacao_semana` se for menor (retrocompat).
    """
    dias = 5  # seg-sex sempre abre
    if not req.sabado_fechado:
        dias += 1
    if not req.domingo_fechado:
        dias += 1
    # Honra valor antigo se for menor (legado)
    return min(dias, req.dias_operacao_semana)


def horas_semanais_operacao(req: SimulateRequest) -> int:
    """Soma das horas de operação na semana (considerando horários por dia)."""
    total = 0
    for dia in range(7):
        horario = get_horario_dia(req, dia)
        if horario is None:
            continue
        total += horario[1] - horario[0]
    return total


def horario_label(req: SimulateRequest) -> str:
    """Label curto pra UI/PDF: '10h-22h · sáb 10h-20h · dom fechado'."""
    seg_sex = f"Seg-Sex {req.hora_abertura}h-{req.hora_fechamento}h"
    sab = (
        "sáb fechado"
        if req.sabado_fechado
        else f"sáb {get_horario_dia(req, 5)[0]}h-{get_horario_dia(req, 5)[1]}h"
    )
    dom = (
        "dom fechado"
        if req.domingo_fechado
        else f"dom {get_horario_dia(req, 6)[0]}h-{get_horario_dia(req, 6)[1]}h"
    )
    return f"{seg_sex} · {sab} · {dom}"
