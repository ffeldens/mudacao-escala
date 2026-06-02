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
    horarios_por_dia: dict[int, tuple[int, int] | None],
    modelo: str,  # '6x1' ou '5x2'
) -> list[Shift]:
    """Aloca FTE × dia × turno conforme heurística, respeitando horário por dia.

    Args:
        fte_full: número de FTEs full (8h + 1h intervalo)
        fte_meio: número de meio-turnos (4h)
        horarios_por_dia: dict {0=seg..6=dom: (abertura, fechamento) ou None}
            None significa loja fechada nesse dia.
        modelo: '6x1' ou '5x2' (define quantos dias de folga por FTE)

    Patterns por dia operacional:
    - Full A (manhã): abertura_dia → +9h
    - Full B (tarde): fechamento_dia -9h → fechamento_dia
    - Meio:           14h-18h (clipado pra dentro do horário do dia)
    """
    shifts: list[Shift] = []

    # Dias que a loja efetivamente abre
    dias_abertos = [d for d in range(7) if horarios_por_dia.get(d) is not None]
    num_dias_abertos = len(dias_abertos)

    # ===== Dias de folga por modelo =====
    if modelo == "5x2":
        dias_folga_por_fte = max(0, num_dias_abertos - 5)
    else:  # 6x1
        dias_folga_por_fte = max(0, num_dias_abertos - 6)

    # ===== Folgas: rotação sobre os dias abertos =====
    # Preferência: dias com menor movimento (seg/ter) — não dom/sáb/sex
    # Mantém só dias abertos na lista de preferência
    folga_pref = [d for d in [0, 1, 2, 3] if d in dias_abertos]
    if not folga_pref and dias_abertos:
        folga_pref = dias_abertos[:1]

    def folgas_do_fte(fte_idx: int) -> set[int]:
        if dias_folga_por_fte == 0 or not folga_pref:
            return set()
        offset = fte_idx % len(folga_pref)
        folgas: set[int] = set()
        for i in range(dias_folga_por_fte):
            folgas.add(folga_pref[(offset + i) % len(folga_pref)])
        return folgas

    def patterns_do_dia(dia: int) -> tuple[
        tuple[int, int, tuple[int, int]],  # A
        tuple[int, int, tuple[int, int]],  # B
        tuple[int, int],                   # meio
    ]:
        """Patterns ajustados pra abertura/fechamento DESTE dia."""
        ab, fc = horarios_por_dia[dia]
        # Full A
        pat_a_ini = ab
        pat_a_fim = min(ab + 9, fc)
        pat_a_intv = (pat_a_ini + 4, pat_a_ini + 5)
        # Full B
        pat_b_fim = fc
        pat_b_ini = max(fc - 9, ab)
        pat_b_intv = (pat_b_ini + 4, pat_b_ini + 5)
        # Meio (pico)
        meio_ini = max(14, ab)
        meio_fim = min(meio_ini + 4, fc)
        return (
            (pat_a_ini, pat_a_fim, pat_a_intv),
            (pat_b_ini, pat_b_fim, pat_b_intv),
            (meio_ini, meio_fim),
        )

    # ===== Aloca FULL =====
    for i in range(fte_full):
        folgas = folgas_do_fte(i)
        for dia in dias_abertos:
            if dia in folgas:
                continue
            (pat_a, pat_b, _meio) = patterns_do_dia(dia)
            # Pattern alternado por FTE
            ini, fim, intv = pat_a if i % 2 == 0 else pat_b
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
        for dia in dias_abertos:
            if dia in folgas:
                continue
            (_a, _b, meio) = patterns_do_dia(dia)
            meio_ini, meio_fim = meio
            shifts.append(
                Shift(
                    fte_idx=fte_idx, tipo="meio", dia=dia,
                    inicio=meio_ini, fim=meio_fim, intervalo=None,
                )
            )

    return shifts


def shifts_to_grade(
    shifts: list[Shift],
    horarios_por_dia: dict[int, tuple[int, int] | None],
    grade_inicio: int,
    grade_fim: int,
) -> ScheduleResult:
    """Converte lista de shifts em grade [dia][hora] e métricas.

    Args:
        shifts: shifts alocados
        horarios_por_dia: horários por dia (pra calcular slots descobertos)
        grade_inicio: hora mínima global pra dimensionar colunas da grade
        grade_fim: hora máxima global (exclusivo)
    """
    horas_grade = max(0, grade_fim - grade_inicio)
    grade = [[0] * horas_grade for _ in range(7)]

    fte_meio_idxs: set[int] = set()
    fte_full_idxs: set[int] = set()

    for s in shifts:
        if 0 <= s.dia < 7:
            for h in range(s.inicio, s.fim):
                if h < grade_inicio or h >= grade_fim:
                    continue
                # Pula horas de intervalo
                if s.intervalo and s.intervalo[0] <= h < s.intervalo[1]:
                    continue
                grade[s.dia][h - grade_inicio] += 1
        if s.tipo == "meio":
            fte_meio_idxs.add(s.fte_idx)
        else:
            fte_full_idxs.add(s.fte_idx)

    # Slots descobertos: só conta nas horas operacionais de cada dia
    slots_descobertos = 0
    slots_total = 0
    for dia in range(7):
        horario = horarios_por_dia.get(dia)
        if horario is None:
            continue
        ab, fc = horario
        for h in range(ab, fc):
            if h < grade_inicio or h >= grade_fim:
                continue
            slots_total += 1
            if grade[dia][h - grade_inicio] == 0:
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


def build_schedule_from_horarios(
    fte_count: float,
    arredondamento_mode: str,
    horarios_por_dia: dict[int, tuple[int, int] | None],
    modelo: str,
) -> ScheduleResult:
    """Pipeline completo: split FTE → aloca → grade.

    Calcula bounds da grade (menor abertura, maior fechamento entre dias
    abertos) pra dimensionar as colunas corretamente.
    """
    fte_full, fte_meio = split_fte_full_meio(fte_count, arredondamento_mode)
    shifts = alocar_shifts(
        fte_full=fte_full,
        fte_meio=fte_meio,
        horarios_por_dia=horarios_por_dia,
        modelo=modelo,
    )

    # Bounds globais pra grade (pra colunas serem consistentes)
    aberturas = [h[0] for h in horarios_por_dia.values() if h is not None]
    fechamentos = [h[1] for h in horarios_por_dia.values() if h is not None]
    if not aberturas:
        return ScheduleResult(
            shifts=[], grade=[[]] * 7, slots_descobertos=0, slots_total=0,
            horas_descobertas=0, fte_full_count=0, fte_meio_count=0,
        )

    grade_inicio = min(aberturas)
    grade_fim = max(fechamentos)

    return shifts_to_grade(
        shifts=shifts,
        horarios_por_dia=horarios_por_dia,
        grade_inicio=grade_inicio,
        grade_fim=grade_fim,
    )


def build_schedule_for_pdf(
    fte_count: float,
    arredondamento_mode: str,
    dias_operacao: int,
    hora_abertura: int,
    hora_fechamento: int,
    modelo: str,
) -> ScheduleResult:
    """[DEPRECATED] Pipeline simples — assume mesmo horário todos os dias.

    Mantido pra retrocompat. Pra horários diferenciados por dia,
    use `build_schedule_from_horarios()`.
    """
    horarios = {
        d: (hora_abertura, hora_fechamento) if d < dias_operacao else None
        for d in range(7)
    }
    return build_schedule_from_horarios(
        fte_count=fte_count,
        arredondamento_mode=arredondamento_mode,
        horarios_por_dia=horarios,
        modelo=modelo,
    )
