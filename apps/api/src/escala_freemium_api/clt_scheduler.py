"""Alocação heurística de shifts pro Validador CLT 2.0.

Diferente do Planejador Pro (CSP solver otimizado), aqui é uma
**heurística determinística** que:
- Aloca cada FTE em 1 dos 2 patterns full (manhã ou tarde) com intervalo
  intrajornada de 1h (CLT Art 71)
- Meio-turnos cobrem janela de pico (14h-18h) com 4h corridas (jornada
  <6h, sem necessidade de intervalo)
- Distribui folgas semanais com rotação (5x2: 2 folgas; 6x1: 1)
- Retorna grade slot-por-slot real, não distribuição uniforme

Não é otimização — é representação honesta. Pra escala otimizada
respeitando demanda histórica + comissionistas + função-específico,
use o Planejador Pro.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Shift:
    """Um turno alocado pra um FTE em um dia da semana."""

    fte_idx: int
    tipo: str  # 'full' | 'meio'
    dia: int  # 0=seg, 6=dom
    inicio: int  # hora de entrada (incluído)
    fim: int  # hora de saída (excluído)
    intervalo: tuple[int, int] | None  # (inicio, fim) — só pra full


@dataclass
class ScheduleResult:
    """Resultado da alocação heurística."""

    shifts: list[Shift]
    grade: list[list[int]]  # [dia][hora_index] = nº FTEs presentes
    slots_descobertos: int  # quantos slots (dia × hora de operação) com 0 FTE
    slots_total: int
    horas_descobertas: int  # = slots_descobertos (1 hora cada slot)
    fte_full_count: int
    fte_meio_count: int


def split_fte_full_meio(
    fte_total: float,
    arredondamento_mode: str,
) -> tuple[int, int]:
    """Quebra um total decimal em (full_inteiro, meio_count).

    - 'meio'   : parte fracionária ≥ 0,5 vira 1 meio-turno
    - 'inteiro': tudo round-up pra full (zero meio)
    - 'decimal': round-half-up tradicional (zero meio)
    """
    if arredondamento_mode == "inteiro":
        return math.ceil(fte_total), 0

    if arredondamento_mode == "meio":
        # Próximo múltiplo de 0,5
        meio_steps = math.ceil(fte_total * 2)  # ex: 4.5 → 9 meio-steps
        full = meio_steps // 2
        tem_meio = meio_steps % 2  # 1 se ímpar (= tem meio-turno extra)
        return full, tem_meio

    # decimal (padrão round half up)
    return round(fte_total), 0


def alocar_shifts(
    fte_full: int,
    fte_meio: int,
    dias_operacao: int,
    hora_abertura: int,
    hora_fechamento: int,
    modelo: str,  # '6x1' ou '5x2'
) -> list[Shift]:
    """Aloca FTE × dia × turno conforme heurística.

    Patterns:
    - Full A (manhã): hora_abertura → +9h (8h trab + 1h intervalo no meio)
    - Full B (tarde): hora_fechamento -9h → hora_fechamento (intervalo no meio)
    - Meio (pico):    14h → 18h (cobre janela de pico de varejo)
    """
    shifts: list[Shift] = []

    # ===== Patterns full =====
    # Pattern A: começa abertura
    pat_a_ini = hora_abertura
    pat_a_fim = min(hora_abertura + 9, hora_fechamento)
    pat_a_intv = (pat_a_ini + 4, pat_a_ini + 5)

    # Pattern B: termina fechamento
    pat_b_fim = hora_fechamento
    pat_b_ini = max(hora_fechamento - 9, hora_abertura)
    pat_b_intv = (pat_b_ini + 4, pat_b_ini + 5)

    # ===== Pattern meio (pico) =====
    meio_ini = max(14, hora_abertura)
    meio_fim = min(meio_ini + 4, hora_fechamento)

    # ===== Dias de folga por modelo =====
    if modelo == "5x2":
        dias_folga_por_fte = 2
    else:  # 6x1
        dias_folga_por_fte = 1

    # Se a loja opera menos dias que o modelo prevê, ajusta
    if dias_operacao < (7 - dias_folga_por_fte):
        dias_folga_por_fte = max(0, 7 - dias_operacao)

    # ===== Helper: gera folgas pra um FTE com rotação =====
    # Folgas preferenciais: segunda + terça (menor pico)
    # Pra evitar todos folgarem no mesmo dia, rotaciona o início
    folga_base = [0, 1, 2, 3, 4, 5, 6]  # seg=0 ... dom=6
    # Ordem de preferência das folgas (priorizando dias menos movimentados)
    folga_pref = [0, 1, 2, 3]  # seg, ter, qua, qui

    def folgas_do_fte(fte_idx: int) -> set[int]:
        if dias_folga_por_fte == 0:
            return set()
        # Rotação: cada FTE pega um conjunto de folgas diferente
        offset = fte_idx % len(folga_pref)
        folgas = set()
        for i in range(dias_folga_por_fte):
            folgas.add(folga_pref[(offset + i) % len(folga_pref)])
        return folgas

    # ===== Aloca FULL =====
    for i in range(fte_full):
        # Pattern alternado
        if i % 2 == 0:
            ini, fim, intv = pat_a_ini, pat_a_fim, pat_a_intv
        else:
            ini, fim, intv = pat_b_ini, pat_b_fim, pat_b_intv

        folgas = folgas_do_fte(i)
        for dia in range(7):
            if dia in folgas:
                continue
            if dia >= dias_operacao:
                continue
            shifts.append(
                Shift(
                    fte_idx=i, tipo="full", dia=dia,
                    inicio=ini, fim=fim, intervalo=intv,
                )
            )

    # ===== Aloca MEIO =====
    for j in range(fte_meio):
        fte_idx = fte_full + j
        folgas = folgas_do_fte(fte_idx)
        for dia in range(7):
            if dia in folgas:
                continue
            if dia >= dias_operacao:
                continue
            shifts.append(
                Shift(
                    fte_idx=fte_idx, tipo="meio", dia=dia,
                    inicio=meio_ini, fim=meio_fim, intervalo=None,
                )
            )

    return shifts


def shifts_to_grade(
    shifts: list[Shift],
    hora_abertura: int,
    hora_fechamento: int,
    dias_operacao: int,
) -> ScheduleResult:
    """Converte lista de shifts em grade [dia][hora] e métricas."""
    horas_dia = max(0, hora_fechamento - hora_abertura)
    grade = [[0] * horas_dia for _ in range(7)]

    fte_idxs = set()
    fte_meio_idxs = set()
    fte_full_idxs = set()

    for s in shifts:
        if 0 <= s.dia < 7:
            for h in range(s.inicio, s.fim):
                if h < hora_abertura or h >= hora_fechamento:
                    continue
                # Pula horas de intervalo
                if s.intervalo and s.intervalo[0] <= h < s.intervalo[1]:
                    continue
                grade[s.dia][h - hora_abertura] += 1
        fte_idxs.add(s.fte_idx)
        if s.tipo == "meio":
            fte_meio_idxs.add(s.fte_idx)
        else:
            fte_full_idxs.add(s.fte_idx)

    # Slots descobertos: dias de operação × horas, contando os com 0 FTE
    slots_descobertos = 0
    slots_total = 0
    for dia in range(min(dias_operacao, 7)):
        for h in range(horas_dia):
            slots_total += 1
            if grade[dia][h] == 0:
                slots_descobertos += 1

    return ScheduleResult(
        shifts=shifts,
        grade=grade,
        slots_descobertos=slots_descobertos,
        slots_total=slots_total,
        horas_descobertas=slots_descobertos,
        fte_full_count=len(fte_full_idxs),
        fte_meio_count=len(fte_meio_idxs),
    )


def build_schedule_for_pdf(
    fte_count: float,
    arredondamento_mode: str,
    dias_operacao: int,
    hora_abertura: int,
    hora_fechamento: int,
    modelo: str,
) -> ScheduleResult:
    """Função de alto nível: split FTE → aloca shifts → grade.

    Pronta pra ser chamada pelo render do PDF.
    """
    fte_full, fte_meio = split_fte_full_meio(fte_count, arredondamento_mode)
    shifts = alocar_shifts(
        fte_full=fte_full,
        fte_meio=fte_meio,
        dias_operacao=dias_operacao,
        hora_abertura=hora_abertura,
        hora_fechamento=hora_fechamento,
        modelo=modelo,
    )
    return shifts_to_grade(
        shifts=shifts,
        hora_abertura=hora_abertura,
        hora_fechamento=hora_fechamento,
        dias_operacao=dias_operacao,
    )
