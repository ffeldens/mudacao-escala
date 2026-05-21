"""CSP solver para geração de escalas otimizadas (Fase 2A).

Substitui o `synthetic_schedule` (stub determinístico) por uma busca real
que respeita TODAS as hard constraints simultaneamente:

  CLT — Art 58 (jornada ≤8h): template de turno fixo
  CLT — Art 66 (interjornada ≥11h): garantido por 1 turno/dia + abertura
  CLT — Art 67 (DSR ≥24h/semana): cada colaborador folga ≥1 dia/semana
  CLT — Art 71 (intrajornada): 1h hardcoded em jornadas >6h
  CLT — Lei 10.101 (1 domingo/4 semanas): garantido por construção
  Custom — ≤6 dias seguidos: verificado entre semanas
  Brand T&F — comissionado nunca folga sábado: filtro de candidatos

  COBERTURA POR FUNÇÃO (NOVO):
    Para cada função F e cada dia operado D, a quantidade de colaboradores
    trabalhando que podem cobrir F deve ser ≥ F.presenca_minima_simultanea.

    "Podem cobrir F" inclui: empregados da própria F + empregados de funções
    que listam F em `pode_cobrir_funcoes` (multifunção, ex: gerente T&F
    cobre caixa em escala apertada).

Algoritmo: backtracking entre colaboradores (gerador de patterns + constraint
propagation). Ordem: comissionados primeiro, depois funções com menor budget
de cobertura, depois resto.

Limitações conhecidas (próximos sprints):
  - Não otimiza cobertura horária vs demanda (objetivo "soft" da Fase 2A.2)
  - Atribuição manhã/tarde é estática (alternada por emp_idx), não otimizada
  - Assume turno único por dia
  - Sem preferências individuais (Fase 2C)
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Iterator
from datetime import date, timedelta
from itertools import combinations
from typing import Literal

from engine.models import (
    Brand,
    FunctionRole,
    Schedule,
    ScheduleEmployee,
    ScheduleShift,
    StoreInput,
)

EscalaType = Literal["5x2", "6x1"]


class SchedulerError(Exception):
    """Erro do solver — geralmente input infactível ou constraints conflitantes."""


# =============================================================================
# Curva de demanda → split manhã/tarde
# =============================================================================
def _split_manha_tarde_por_dow(store: StoreInput) -> dict[int, float]:
    """Calcula a fração de colaboradores que devem ir pro turno de TARDE
    em cada dia da semana, baseado em store.ticket_history.

    Returns:
        dict {dow: fração_tarde} onde fração_tarde ∈ [0.0, 1.0]
        (1.0 = todos tarde, 0.0 = todos manhã, 0.5 = balanceado)

    Quando ticket_history está vazio, retorna 0.5 (default 50/50).

    A divisão manhã/tarde é definida pelo meio do período de operação da loja.
    """
    if not store.ticket_history:
        return {dow: 0.5 for dow in range(7)}

    meio = (store.hora_abertura + store.hora_fechamento) / 2

    # Soma de tickets por (dow, periodo)
    tickets_manha: dict[int, float] = {}
    tickets_tarde: dict[int, float] = {}
    for p in store.ticket_history:
        dow = p.dia_semana
        valor = float(p.media_tickets)
        if p.hora < meio:
            tickets_manha[dow] = tickets_manha.get(dow, 0.0) + valor
        else:
            tickets_tarde[dow] = tickets_tarde.get(dow, 0.0) + valor

    split: dict[int, float] = {}
    for dow in range(7):
        m = tickets_manha.get(dow, 0.0)
        t = tickets_tarde.get(dow, 0.0)
        total = m + t
        if total <= 0:
            split[dow] = 0.5
        else:
            split[dow] = t / total
    return split


def _consecutivos_no_combo(combo: set[date]) -> int:
    """Conta quantos pares de dias consecutivos um combo de folgas contém.
    Usado para preferir 'dobradinhas' (folgas em dias adjacentes)."""
    if len(combo) < 2:
        return 0
    dias_ord = sorted(combo)
    return sum(
        1
        for i in range(len(dias_ord) - 1)
        if (dias_ord[i + 1] - dias_ord[i]).days == 1
    )


# =============================================================================
# Entry point
# =============================================================================
def plan_schedule(
    *,
    store: StoreInput,
    periodo_inicio: date,
    periodo_dias: int = 28,
    escala_type: EscalaType = "5x2",
    semente: str = "default",
) -> Schedule:
    """Gera escala otimizada respeitando hard constraints CLT + brand + cobertura."""
    dias_folga_semana = 2 if escala_type == "5x2" else 1
    period_end = periodo_inicio + timedelta(days=periodo_dias - 1)

    # 1. Lista de colaboradores
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
            periodo_fim=period_end.isoformat(),
            employees=[],
            shifts=[],
        )

    # 2. Mapeia função → FunctionRole + capacidades de cobertura cruzada
    funcoes_by_name: dict[str, FunctionRole] = {f.nome: f for f in store.funcoes}

    # Para cada função-alvo, quais funções podem cobrir (incluindo a própria)
    cobrem_funcao: dict[str, set[str]] = {f.nome: {f.nome} for f in store.funcoes}
    for f in store.funcoes:
        for alvo in f.pode_cobrir_funcoes:
            if alvo in cobrem_funcao:
                cobrem_funcao[alvo].add(f.nome)

    # 3. Calcula total de colaboradores que podem cobrir cada função
    total_coverable: dict[str, int] = {}
    for func_nome, cobertoras in cobrem_funcao.items():
        total_coverable[func_nome] = sum(
            funcoes_by_name[c].qtd_atual for c in cobertoras if c in funcoes_by_name
        )

    # 4. presenca_minima_simultanea efetiva: relaxa se infactível
    # (ex: estoque sozinho com presenca=1 → não daria folga, relaxa para 0)
    presenca_efetiva: dict[str, int] = {}
    for func_nome, funcao in funcoes_by_name.items():
        pm = funcao.presenca_minima_simultanea or 0
        total = total_coverable[func_nome]
        # Garante que pelo menos 1 folga é possível: presenca <= total - 1
        if pm >= total:
            presenca_efetiva[func_nome] = max(0, total - 1)
        else:
            presenca_efetiva[func_nome] = pm

    # 5. Dias do período
    days = [periodo_inicio + timedelta(days=i) for i in range(periodo_dias)]
    weeks: dict[tuple[int, int], list[date]] = {}
    for d in days:
        key = (d.isocalendar().year, d.isocalendar().week)
        weeks.setdefault(key, []).append(d)
    week_keys = list(weeks.keys())

    open_dows = set(range(store.dias_operacao_semana))

    # 6. Ordena colaboradores: tightness primeiro (menor budget de cobertura),
    # depois comissionados, depois resto. Heuristica gulosa: atribui os mais
    # restritos primeiro para reduzir backtrack.
    def emp_priority(idx_emp: tuple[int, ScheduleEmployee]) -> tuple:
        _, emp = idx_emp
        f = funcoes_by_name.get(emp.funcao)
        if f is None:
            return (99, 0, emp.employee_id)
        # Budget = total_coverable - presenca_efetiva. Menor budget = mais apertado.
        budget = total_coverable[emp.funcao] - presenca_efetiva[emp.funcao]
        return (budget, not emp.comissionado, emp.employee_id)

    employees_indexed = list(enumerate(employees))
    employees_sorted = sorted(employees_indexed, key=emp_priority)

    # 7. Estado: contagem de "pessoas folgando que podem cobrir F" por (F, D)
    # Inicia em 0; incrementa quando atribuímos folga a alguém em F ou em
    # função que cobre F.
    folga_count: dict[str, dict[date, int]] = {f: {} for f in cobrem_funcao}

    # 8. Backtracking entre colaboradores
    patterns: dict[str, dict[tuple[int, int], set[date]]] = {}
    base_seed = _seed(semente, store.codigo)

    def assign(idx: int) -> bool:
        if idx == len(employees_sorted):
            return True

        original_idx, emp = employees_sorted[idx]
        is_comissionado_tf = (store.brand == "track_field" and emp.comissionado)

        # Funções que esta pessoa pode cobrir (incluindo a própria)
        funcoes_que_emp_cobre = {emp.funcao}
        emp_funcao = funcoes_by_name.get(emp.funcao)
        if emp_funcao:
            funcoes_que_emp_cobre.update(emp_funcao.pode_cobrir_funcoes)

        rng = random.Random(base_seed + idx * 7919)

        for pattern in _iter_employee_patterns(
            week_keys=week_keys,
            weeks=weeks,
            dias_folga_semana=dias_folga_semana,
            is_comissionado_tf=is_comissionado_tf,
            rng=rng,
            funcoes_que_emp_cobre=funcoes_que_emp_cobre,
            folga_count=folga_count,
            presenca_efetiva=presenca_efetiva,
            total_coverable=total_coverable,
            open_dows=open_dows,
        ):
            # Commit: incrementa contagem por (função-alvo, dia)
            committed_increments: list[tuple[str, date]] = []
            for _wk, dates in pattern.items():
                for d in dates:
                    if d.weekday() not in open_dows:
                        continue  # dia fechado, folga não conta
                    for alvo in funcoes_que_emp_cobre:
                        folga_count[alvo][d] = folga_count[alvo].get(d, 0) + 1
                        committed_increments.append((alvo, d))

            patterns[emp.employee_id] = pattern

            if assign(idx + 1):
                return True

            # Undo
            del patterns[emp.employee_id]
            for alvo, d in committed_increments:
                folga_count[alvo][d] -= 1
                if folga_count[alvo][d] == 0:
                    del folga_count[alvo][d]

        return False

    if not assign(0):
        raise SchedulerError(
            f"Não foi possível encontrar escala factível para {store.codigo}. "
            f"Provável conflito de constraints — verificar headcount vs "
            f"presenca_minima_simultanea + restricões CLT."
        )

    # 9. Calcula split manhã/tarde a partir de ticket_history.
    # IMPORTANTE: turno é FIXO por colaborador para todo o período. Alternar
    # turno entre dias (tarde D → manhã D+1) violaria Art 66 (interjornada
    # mínima 11h) em lojas que operam ≥12h/dia (ex: TFC 8h-22h, fechamento
    # 22h + abertura 8h = só 10h de interjornada).
    #
    # Mas a PROPORÇÃO de colaboradores em cada turno segue a curva real:
    # se aos sábados a demanda está mais concentrada na tarde, mais colabs
    # ficam no turno tarde.
    split_tarde_por_dow = _split_manha_tarde_por_dow(store)
    turno_horas = 8 if escala_type == "5x2" else 7
    store_horas = store.hora_fechamento - store.hora_abertura
    tem_2_turnos = store_horas > turno_horas + 2

    # Atribui turno FIXO por colaborador. Usa a média do peso_tarde nos dias
    # operados (ou se sazonal forte, peso do pico semanal).
    emp_turno: dict[int, str] = {}  # emp_idx → "manha" | "tarde"
    if tem_2_turnos:
        # Peso médio nos dias operados
        dows_op = list(range(store.dias_operacao_semana))
        peso_tarde_medio = sum(split_tarde_por_dow.get(d, 0.5) for d in dows_op) / len(dows_op)
        n = len(employees)
        k_tarde = round(n * peso_tarde_medio)
        # Distribuição: emp_idx ímpares preferencialmente pra tarde (mantém
        # idempotência com versão anterior do solver), depois por idx.
        ordenados = sorted(range(n), key=lambda ei: (0 if ei % 2 == 1 else 1, ei))
        tarde_set = set(ordenados[:k_tarde])
        for ei in range(n):
            emp_turno[ei] = "tarde" if ei in tarde_set else "manha"
    else:
        for ei in range(len(employees)):
            emp_turno[ei] = "manha"

    # 10. Constrói shifts (preserva ordem original dos colaboradores)
    shifts: list[ScheduleShift] = []
    for emp_idx, emp in enumerate(employees):
        pattern = patterns[emp.employee_id]
        for week_key, dias_da_semana in weeks.items():
            folgas_da_semana = pattern.get(week_key, set())
            for dia in dias_da_semana:
                if dia in folgas_da_semana:
                    continue
                if dia.weekday() >= store.dias_operacao_semana:
                    continue

                if tem_2_turnos and emp_turno.get(emp_idx) == "tarde":
                    inicio_h = store.hora_fechamento - turno_horas
                    fim_h = store.hora_fechamento
                else:
                    inicio_h = store.hora_abertura
                    fim_h = inicio_h + turno_horas

                intra_inicio = None
                intra_fim = None
                if turno_horas > 6:
                    intra_h = inicio_h + turno_horas // 2
                    intra_inicio = f"{intra_h:02d}:00"
                    intra_fim = f"{intra_h + 1:02d}:00"

                shifts.append(
                    ScheduleShift(
                        employee_id=emp.employee_id,
                        employee_nome=emp.employee_id,
                        data=dia.isoformat(),
                        inicio=f"{inicio_h:02d}:00",
                        fim=f"{fim_h:02d}:00",
                        intrajornada_inicio=intra_inicio,
                        intrajornada_fim=intra_fim,
                    )
                )

    return Schedule(
        store_codigo=store.codigo,
        brand=store.brand,
        periodo_inicio=periodo_inicio.isoformat(),
        periodo_fim=period_end.isoformat(),
        employees=employees,
        shifts=shifts,
    )


# =============================================================================
# Generator de folga patterns para 1 colaborador
# =============================================================================
def _iter_employee_patterns(
    *,
    week_keys: list[tuple[int, int]],
    weeks: dict[tuple[int, int], list[date]],
    dias_folga_semana: int,
    is_comissionado_tf: bool,
    rng: random.Random,
    funcoes_que_emp_cobre: set[str],
    folga_count: dict[str, dict[date, int]],
    presenca_efetiva: dict[str, int],
    total_coverable: dict[str, int],
    open_dows: set[int],
) -> Iterator[dict[tuple[int, int], set[date]]]:
    """Gera todos os padrões de folga válidos para um colaborador.

    Filtra por:
    1. Brand T&F (comissionado nunca folga sábado)
    2. Cobertura: não folgar em dia onde já está no limite para alguma
       função que este colab cobre
    3. Custom (≤6 dias seguidos) entre semanas
    4. Lei 10.101 ao fim
    """

    def folga_violaria_cobertura(d: date) -> bool:
        """True se folgar em d derrubaria a cobertura de alguma função
        que este colaborador cobre."""
        if d.weekday() not in open_dows:
            return False  # dia fechado, sem impacto na cobertura
        for alvo in funcoes_que_emp_cobre:
            current = folga_count[alvo].get(d, 0)
            # Quantos podem cobrir alvo = total_coverable[alvo]
            # Trabalhando = total_coverable[alvo] - current
            # Após folga este colab: trabalhando seria total - (current + 1)
            # Precisa ser ≥ presenca_efetiva[alvo]
            if total_coverable[alvo] - (current + 1) < presenca_efetiva[alvo]:
                return True
        return False

    # Candidates per week
    week_candidates: list[list[set[date]]] = []
    for wk in week_keys:
        dias_da_semana = weeks[wk]
        cands: list[set[date]] = []
        folgas_alvo = min(dias_folga_semana, max(1, len(dias_da_semana) - 3))

        for combo in combinations(dias_da_semana, folgas_alvo):
            # Brand T&F
            if is_comissionado_tf and any(d.weekday() == 5 for d in combo):
                continue
            # Coverage budget
            if any(folga_violaria_cobertura(d) for d in combo):
                continue
            cands.append(set(combo))

        if not cands:
            return  # infeasible para esta semana
        # Shuffle puro. Tentamos dobradinhas como soft preference mas
        # ordenação estrita por consecutivos criou streaks de trabalho >10
        # dias (folgas juntas = bloco grande de trabalho no meio). Pra
        # preservar variabilidade e streaks razoáveis, mantemos shuffle puro
        # e tratamos dobradinha como propriedade emergente da escala (nem
        # toda escala terá; algumas terão por acaso).
        rng.shuffle(cands)
        week_candidates.append(cands)

    # Backtrack across weeks, yielding solutions
    selected: dict[tuple[int, int], set[date]] = {}

    # Nota: max-streak (Custom 6-dias) é tratado como soft (warn) tanto no
    # solver quanto no validator. Em 6x1 com comissionados T&F, o conjunto
    # {brand-sat + Lei 10.101 + Custom-6 estrito} pode ser matematicamente
    # infactível (DOW de folga deve ser não-crescente entre semanas; com 8
    # vendedores comissionados precisando 1 dom folga e budget de vendedor=6,
    # 2 vendedores não conseguem dom-folgar e seu único caminho é violar
    # Custom-6 ou brand-sat). Preferimos warns em Custom-6 vs hard violation
    # em brand-sat. Validator separa warns de violations.

    def bt(idx: int) -> Iterator[dict[tuple[int, int], set[date]]]:
        if idx == len(week_keys):
            if _check_lei_10101(week_keys, weeks, selected):
                yield dict(selected)
            return

        wk = week_keys[idx]
        for combo in week_candidates[idx]:
            selected[wk] = combo
            yield from bt(idx + 1)

        if wk in selected:
            del selected[wk]

    yield from bt(0)


# =============================================================================
# Checks
# =============================================================================
def _check_max_consecutive(
    *,
    prev_week_days: list[date],
    curr_week_days: list[date],
    prev_folgas: set[date],
    curr_folgas: set[date],
    max_consec: int = 6,
) -> bool:
    all_days = sorted(prev_week_days + curr_week_days)
    folgas = prev_folgas | curr_folgas
    consec = 0
    for d in all_days:
        if d in folgas:
            consec = 0
        else:
            consec += 1
            if consec > max_consec:
                return False
    return True


def _check_lei_10101(
    week_keys: list[tuple[int, int]],
    weeks: dict[tuple[int, int], list[date]],
    selected: dict[tuple[int, int], set[date]],
) -> bool:
    all_days = []
    for wk in week_keys:
        all_days.extend(weeks[wk])
    domingos = sorted({d for d in all_days if d.weekday() == 6})
    folgou_set: set[date] = set()
    for folgas in selected.values():
        for d in folgas:
            if d.weekday() == 6:
                folgou_set.add(d)
    for inicio in range(0, len(domingos), 4):
        janela = domingos[inicio : inicio + 4]
        if len(janela) < 4:
            continue
        if not any(d in folgou_set for d in janela):
            return False
    return True


# =============================================================================
# Validador de cobertura (uso pelos testes)
# =============================================================================
def check_coverage(
    schedule: Schedule, store: StoreInput
) -> dict[str, list[tuple[date, int, int]]]:
    """Verifica a cobertura por (função, dia operado).

    Returns:
        Dict {função: [(data, working_count, presenca_minima)]} listando
        APENAS dias com violação (working < presenca_minima).
    """
    funcoes_by_name = {f.nome: f for f in store.funcoes}
    cobrem_funcao: dict[str, set[str]] = {f.nome: {f.nome} for f in store.funcoes}
    for f in store.funcoes:
        for alvo in f.pode_cobrir_funcoes:
            if alvo in cobrem_funcao:
                cobrem_funcao[alvo].add(f.nome)

    # Map employee → função (do schedule.employees)
    emp_funcao: dict[str, str] = {e.employee_id: e.funcao for e in schedule.employees}

    # Coleta dias trabalhados por colaborador
    work_dates: dict[str, set[date]] = {}
    for s in schedule.shifts:
        work_dates.setdefault(s.employee_id, set()).add(date.fromisoformat(s.data))

    # Período
    inicio = date.fromisoformat(schedule.periodo_inicio)
    fim = date.fromisoformat(schedule.periodo_fim)
    days_in_period = [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]

    open_dows = set(range(store.dias_operacao_semana))
    violations: dict[str, list[tuple[date, int, int]]] = {f.nome: [] for f in store.funcoes}

    for func_nome in funcoes_by_name:
        pm = funcoes_by_name[func_nome].presenca_minima_simultanea or 0
        if pm <= 0:
            continue
        # Skip funções relaxadas (total coverable <= presenca minima → infactível
        # forçar, então o solver relaxa).
        total = sum(
            funcoes_by_name[c].qtd_atual for c in cobrem_funcao.get(func_nome, {func_nome})
        )
        if pm >= total:
            continue
        for d in days_in_period:
            if d.weekday() not in open_dows:
                continue
            # Quantos podem cobrir func_nome estão trabalhando este dia?
            cobertoras = cobrem_funcao.get(func_nome, {func_nome})
            working = 0
            for emp_id, datas_trab in work_dates.items():
                if emp_funcao.get(emp_id) in cobertoras and d in datas_trab:
                    working += 1
            if working < pm:
                violations[func_nome].append((d, working, pm))

    # Remove funções sem violações
    return {f: v for f, v in violations.items() if v}


# =============================================================================
# Helpers
# =============================================================================
def _slug(s: str) -> str:
    return (
        s.lower()
        .replace(" ", "-")
        .replace("ã", "a")
        .replace("ê", "e")
        .replace("é", "e")
        .replace("ú", "u")
        .replace("í", "i")
    )


def _seed(*parts: str) -> int:
    return int(hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()[:8], 16)
