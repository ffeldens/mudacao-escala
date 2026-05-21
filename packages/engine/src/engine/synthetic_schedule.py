"""Gerador de escalas sintéticas para alimentar o validador CLT sem dados reais.

Gera escalas mensais (ou de N dias) seguindo padrões 6x1 ou 5x2, distribuindo
folgas entre os colaboradores. Útil para:
- Demonstrar o validador CLT na UI sem precisar de dados do cliente
- Testar regressões do validador
- Stress-test (gerar escalas com violações deliberadas)

NÃO é o algoritmo de planejamento da Fase 2A — é um stub determinístico
que produz escalas plausíveis mas sem otimização.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from typing import Literal

from engine.models import Brand, Schedule, ScheduleEmployee, ScheduleShift, StoreInput

EscalaType = Literal["5x2", "6x1"]


def generate_synthetic_schedule(
    *,
    store: StoreInput,
    escala_type: EscalaType = "5x2",
    periodo_inicio: date,
    periodo_dias: int = 28,
    incluir_violacoes_propositais: bool = False,
    semente: str = "default",
) -> Schedule:
    """Gera uma escala sintética para a loja no período informado.

    Args:
        store: dados da loja (define horários, funções, headcount).
        escala_type: "5x2" (2 folgas/sem) ou "6x1" (1 folga/sem).
        periodo_inicio: data de início (segunda-feira recomendada).
        periodo_dias: total de dias (default 28 = 4 semanas).
        incluir_violacoes_propositais: se True, injeta 1-2 violações CLT
            intencionais (jornada >8h, intrajornada faltante, interjornada
            curta) — útil para demonstrar o validador.
        semente: torna a geração determinística por loja+período.

    Returns:
        Schedule com shifts distribuídos entre os colaboradores.
    """
    rng = random.Random(_seed(semente, store.codigo, periodo_inicio.isoformat()))

    # Cria lista flat de colaboradores com função + flag comissionado.
    employees: list[ScheduleEmployee] = []
    for funcao in store.funcoes:
        for i in range(funcao.qtd_atual):
            emp_id = f"{store.codigo}-{_slug(funcao.nome)}-{i+1:02d}"
            employees.append(
                ScheduleEmployee(
                    employee_id=emp_id,
                    funcao=funcao.nome,
                    comissionado=funcao.comissionado,
                )
            )

    if not employees:
        return Schedule(
            store_codigo=store.codigo,
            brand=store.brand,
            periodo_inicio=periodo_inicio.isoformat(),
            periodo_fim=(periodo_inicio + timedelta(days=periodo_dias - 1)).isoformat(),
            employees=[],
            shifts=[],
        )

    # Padrão de folgas:
    # 5x2 → cada colaborador trabalha 5 dias e folga 2 (rotativo)
    # 6x1 → trabalha 6 e folga 1
    dias_trabalho_semana = 5 if escala_type == "5x2" else 6
    dias_folga_semana = 7 - dias_trabalho_semana

    # Padrão de turno: jornada de 8h (5x2) ou 7h20min (6x1, p/ caber em 44h/sem)
    jornada_horas = 8 if escala_type == "5x2" else 7

    shifts: list[ScheduleShift] = []
    for emp_idx, emp in enumerate(employees):
        emp_id = emp.employee_id
        is_comissionado_tf = (store.brand == "track_field" and emp.comissionado)

        for dia in range(periodo_dias):
            data = periodo_inicio + timedelta(days=dia)
            dow = data.weekday()  # 0=segunda, 5=sábado, 6=domingo
            semana_index = dia // 7

            # Cada colaborador tem fase diferente que rotaciona semanalmente.
            # Trade-off conhecido: passo 1 mantem streaks <=5 dias (sem violar
            # Custom 6-dias) mas pode deixar 2/7 colaboradores sem folga em
            # nenhum domingo numa janela de 4 semanas (violando Lei 10.101);
            # passo 2 cobre todos domingos mas cria streaks de ate 10 dias.
            # Este eh um stub determinístico — uma escala "ideal" exige o CSP
            # solver da Fase 2A. Ver tests/test_clt_validator.py para os
            # invariantes que o stub garante (Art 58/66/71) vs os que ficam
            # como TODO (Art 67 / Lei 10.101 / Custom em alguns casos).
            offset_folga = (emp_idx + semana_index) % 7

            # Decide se é folga
            posicao_no_ciclo = (dia + offset_folga) % 7
            is_folga = posicao_no_ciclo < dias_folga_semana

            # Brand rule T&F: comissionado NÃO folga sábado.
            # Quando incluir_violacoes_propositais, pula em ~30% dos casos.
            if (
                is_folga
                and is_comissionado_tf
                and dow == 5
                and not (incluir_violacoes_propositais and rng.random() < 0.3)
            ):
                is_folga = False

            if is_folga:
                continue

            # Se a loja não opera neste DOW, pula
            if dow >= store.dias_operacao_semana:
                continue

            # Define horário do turno: distribui em 2 turnos (manhã/tarde)
            # para cobrir toda a jornada da loja.
            tem_2_turnos = (
                store.hora_fechamento - store.hora_abertura
            ) > jornada_horas + 2

            if tem_2_turnos and emp_idx % 2 == 1:
                # Turno tarde
                inicio_h = store.hora_fechamento - jornada_horas
                fim_h = store.hora_fechamento
            else:
                # Turno manhã
                inicio_h = store.hora_abertura
                fim_h = inicio_h + jornada_horas

            inicio_str = f"{inicio_h:02d}:00"
            fim_str = f"{fim_h:02d}:00"

            # Intrajornada de 1h no meio do turno (jornada >6h)
            intra_inicio = None
            intra_fim = None
            if jornada_horas > 6:
                intra_h = inicio_h + jornada_horas // 2
                intra_inicio = f"{intra_h:02d}:00"
                intra_fim = f"{intra_h + 1:02d}:00"

            # Violações propositais (se solicitado): aplica em ~10% dos shifts
            if incluir_violacoes_propositais and rng.random() < 0.10:
                violacao = rng.choice(["jornada_longa", "sem_intrajornada"])
                if violacao == "jornada_longa":
                    fim_str = f"{min(inicio_h + 10, 23):02d}:00"  # 10h de jornada
                elif violacao == "sem_intrajornada":
                    intra_inicio = None
                    intra_fim = None

            shifts.append(
                ScheduleShift(
                    employee_id=emp_id,
                    employee_nome=emp_id,
                    data=data.isoformat(),
                    inicio=inicio_str,
                    fim=fim_str,
                    intrajornada_inicio=intra_inicio,
                    intrajornada_fim=intra_fim,
                )
            )

    return Schedule(
        store_codigo=store.codigo,
        brand=store.brand,
        periodo_inicio=periodo_inicio.isoformat(),
        periodo_fim=(periodo_inicio + timedelta(days=periodo_dias - 1)).isoformat(),
        employees=employees,
        shifts=shifts,
    )


def _seed(*parts: str) -> int:
    """Gera semente determinística a partir de strings."""
    s = "|".join(parts)
    return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16)


def _slug(s: str) -> str:
    """Slug simples para usar em employee_id."""
    return (
        s.lower()
        .replace(" ", "-")
        .replace("ã", "a")
        .replace("ê", "e")
        .replace("é", "e")
        .replace("ú", "u")
        .replace("í", "i")
    )
